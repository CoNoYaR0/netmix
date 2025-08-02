import asyncio
import time
import logging
import csv
import os
import re
from collections import deque

class ConnectionManager:
    """
    Manages and monitors the health of all available network interfaces.

    This class is the single source of truth for all network statistics,
    including latency history, success/failure rates, and active connection counts.
    It is designed to be thread-safe.
    """
    def __init__(self, interfaces, check_interval=10, history_len=20, zt_api=None):
        self.interfaces = interfaces
        self.check_interval = check_interval
        self.history_len = history_len
        self.zt_api = zt_api  # ZeroTier API client
        self.check_host = 'www.google.com'  # Default host for non-ZT interfaces
        self.check_port = 80
        self.running = False
        self.lock = asyncio.Lock()

        self.health_data = {}
        for name in self.interfaces:
            self.health_data[name] = {
                'latencies': deque(maxlen=self.history_len),
                'successes': 0,
                'failures': 0,
                'active_conns': 0,
                'bytes_sent': 0,
                'bytes_received': 0
            }

        logging.info(f"Connection Manager initialized for interfaces: {list(self.interfaces.keys())}")

    async def check_latency(self, local_ip, host, port):
        """Measures latency by timing a TCP connection and returns it in ms."""
        try:
            start_time = time.monotonic()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, local_addr=(local_ip, 0)),
                timeout=3
            )
            end_time = time.monotonic()
            writer.close()
            await writer.wait_closed()
            return (end_time - start_time) * 1000
        except (OSError, asyncio.TimeoutError) as e:
            logging.warning(f"Latency check failed for IP {local_ip} against host {host}: {e}")
            return 9999.0

    def stop_health_checks(self):
        self.running = False

    async def record_success(self, interface_name):
        if interface_name in self.health_data:
            async with self.lock:
                self.health_data[interface_name]['successes'] += 1

    async def record_failure(self, interface_name):
        if interface_name in self.health_data:
            async with self.lock:
                self.health_data[interface_name]['failures'] += 1

    async def record_bytes_sent(self, interface_name, num_bytes):
        if interface_name in self.health_data:
            async with self.lock:
                self.health_data[interface_name]['bytes_sent'] += num_bytes

    async def record_bytes_received(self, interface_name, num_bytes):
        if interface_name in self.health_data:
            async with self.lock:
                self.health_data[interface_name]['bytes_received'] += num_bytes

    async def increment_active_conn(self, interface_name):
        if interface_name in self.health_data:
            async with self.lock:
                self.health_data[interface_name]['active_conns'] += 1

    async def decrement_active_conn(self, interface_name):
        if interface_name in self.health_data:
            async with self.lock:
                self.health_data[interface_name]['active_conns'] -= 1

    def get_health_data(self):
        # No lock needed for a simple read, as it's an atomic operation in Python.
        return self.health_data

    def _log_to_csv(self, data_row):
        """Appends a row of data to the training log file."""
        log_file = 'netmix_training_data.csv'
        write_header = not os.path.exists(log_file)

        with open(log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(['timestamp', 'interface_name', 'latency', 'successes', 'failures', 'active_conns'])
            writer.writerow(data_row)

    async def run_health_checks(self):
        """Periodically checks the latency of all interfaces and logs data."""
        self.running = True
        logging.info("Connection Manager's health checker started.")
        while self.running:
            failed_checks = 0
            for name, ip in self.interfaces.items():
                host_to_check = self.check_host
                port_to_check = self.check_port

                # If this is a ZeroTier interface, try to find its gateway for a more reliable health check.
                if self.zt_api and 'zerotier' in name.lower():
                    logging.debug(f"Interface '{name}' is a ZeroTier adapter. Attempting to find its gateway.")
                    match = re.search(r'\[([a-f0-9]{16})\]', name, re.IGNORECASE)
                    if match:
                        network_id = match.group(1)
                        try:
                            network_details = self.zt_api.get_network(network_id)
                            # Find the default route (0.0.0.0/0)
                            default_route = next((r for r in network_details.get('routes', []) if r.get('target') == '0.0.0.0/0' and r.get('via')), None)
                            if default_route and default_route.get('via'):
                                host_to_check = default_route['via']
                                logging.info(f"Using ZeroTier gateway {host_to_check} for latency check on '{name}'.")
                            else:
                                logging.info(f"No default route configured for ZT network {network_id}. Using default check host.")
                        except Exception as e:
                            logging.warning(f"Could not retrieve ZT network details for '{network_id}': {e}. Using default check host.")

                latency = await self.check_latency(ip, host_to_check, port_to_check)
                timestamp = time.time()

                if latency >= 9999.0:
                    failed_checks += 1

                async with self.lock:
                    health_snapshot = self.health_data[name]
                    health_snapshot['latencies'].append(latency)

                    # Log the state *before* this check for training purposes
                    self._log_to_csv([
                        timestamp,
                        name,
                        latency,
                        health_snapshot['successes'],
                        health_snapshot['failures'],
                        health_snapshot['active_conns']
                    ])

                logging.info(f"Latency for {name} ({ip}): {latency:.2f} ms")

            # If all interfaces failed, we might be offline. Pause for a while.
            if len(self.interfaces) > 0 and failed_checks == len(self.interfaces):
                logging.warning("All interfaces failed latency checks. Possible network outage. Pausing checks for 60 seconds.")
                await asyncio.sleep(60)
            else:
                await asyncio.sleep(self.check_interval)
