import asyncio
import time
import logging

# Dictionaries to be shared between the proxy, health checker, and dashboard.
interface_latency = {} # Stores { 'interface_name': latency_ms }
connection_counts = {} # Stores { 'interface_name': count }

class HealthChecker:
    def __init__(self, interfaces, check_interval=10):
        """
        interfaces: A list of (name, ip) tuples.
        check_interval: How often to check latency, in seconds.
        """
        self.interfaces = interfaces
        # Initialize latencies to a high value
        for name, _ in self.interfaces:
            interface_latency[name] = 9999

        self.check_interval = check_interval
        self.check_host = 'www.google.com'
        self.check_port = 80
        self.running = False

    async def check_latency(self, local_ip):
        """Measures latency by timing a TCP connection."""
        try:
            start_time = time.monotonic()
            # Use a timeout to avoid waiting too long for a dead interface
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.check_host, self.check_port, local_addr=(local_ip, 0)),
                timeout=3
            )
            end_time = time.monotonic()
            writer.close()
            await writer.wait_closed()
            # Return latency in milliseconds
            return (end_time - start_time) * 1000
        except (OSError, asyncio.TimeoutError) as e:
            logging.warning(f"Latency check failed for interface {local_ip}: {e}")
            return 9999 # Return a high value for failed checks

    async def run(self):
        """Periodically checks the latency of all interfaces."""
        self.running = True
        logging.info("Health checker started.")
        while self.running:
            for name, ip in self.interfaces:
                latency = await self.check_latency(ip)
                interface_latency[name] = latency
                logging.info(f"Latency for {name} ({ip}): {latency:.2f} ms")

            await asyncio.sleep(self.check_interval)

    def stop(self):
        self.running = False
