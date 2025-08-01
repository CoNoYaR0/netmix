import asyncio
import time
import logging
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

    async def run_health_checks(self):
        """Periodically checks the latency of all interfaces."""
        self.running = True
        logging.info("Connection Manager's health checker started.")
        while self.running:
            for name, ip in self.interfaces.items():
                latency = await self.check_latency(ip)
                async with self.lock:
                    self.health_data[name]['latencies'].append(latency)
                logging.info(f"Latency for {name} ({ip}): {latency:.2f} ms")

            await asyncio.sleep(self.check_interval)

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
