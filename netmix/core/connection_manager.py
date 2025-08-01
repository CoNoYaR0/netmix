import asyncio
import time
import logging
import csv
import os
from collections import deque

class ConnectionManager:
    """
    Manages and monitors the health of all available network interfaces.

    This class is the single source of truth for all network statistics,
    including latency history, success/failure rates, and active connection counts.
    It is designed to be thread-safe.
    """
    def __init__(self, interfaces, check_interval=10, history_len=20):
        self.interfaces = interfaces
        self.check_interval = check_interval
        self.history_len = history_len
        self.check_host = 'www.google.com'
        self.check_port = 80
        self.running = False
        self.lock = asyncio.Lock()

        self.health_data = {}
        for name in self.interfaces:
            self.health_data[name] = {
                'latencies': deque(maxlen=self.history_len),
                'successes': 0,
                'failures': 0,
                'active_conns': 0
            }

        logging.info(f"Connection Manager initialized for interfaces: {list(self.interfaces.keys())}")

    async def check_latency(self, local_ip):
        """Measures latency by timing a TCP connection and returns it in ms."""
        try:
            start_time = time.monotonic()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.check_host, self.check_port, local_addr=(local_ip, 0)),
                timeout=3
            )
            end_time = time.monotonic()
            writer.close()
            await writer.wait_closed()
            return (end_time - start_time) * 1000
        except (OSError, asyncio.TimeoutError) as e:
            logging.warning(f"Latency check failed for IP {local_ip}: {e}")
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
            for name, ip in self.interfaces.items():
                latency = await self.check_latency(ip)
                timestamp = time.time()

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

            await asyncio.sleep(self.check_interval)
