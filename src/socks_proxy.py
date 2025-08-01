import asyncio
import socket
import logging
from interface_manager import get_active_interfaces
from health_checker import HealthChecker, interface_latency, connection_counts

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SOCKS_VERSION = 5
NO_AUTH = 0x00
CMD_CONNECT = 0x01
ATYP_IPV4 = 0x01
ATYP_DOMAIN = 0x03

async def forward_data(reader, writer, direction):
    """Read from a reader and write to a writer until EOF."""
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            writer.write(data)
            await writer.drain()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logging.warning(f"Forwarding task ({direction}) ended with error: {e}")
    finally:
        writer.close()

class SocksProxy:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.server = None
        self.health_checker_task = None
        self.interfaces = get_active_interfaces()
        self.interface_list = list(self.interfaces.items())
        self.conn_counter_lock = asyncio.Lock()

        if not self.interface_list:
            logging.warning("No active network interfaces found for routing. Will use default.")
            self.health_checker = None
        else:
            logging.info(f"Proxy will manage interfaces: {list(self.interfaces.keys())}")
            self.health_checker = HealthChecker(self.interface_list)
            # Initialize connection counts
            for name, _ in self.interface_list:
                connection_counts[name] = 0

    async def handle_client(self, client_reader, client_writer):
        client_addr = client_writer.get_extra_info('peername')
        logging.info(f"New connection from {client_addr}")

        remote_writer = None
        iface_name_used = None
        try:
            # === SOCKS Handshake ===
            header = await client_reader.read(2)
            if not header or header[0] != SOCKS_VERSION: raise ConnectionAbortedError("Bad SOCKS version")
            nmethods = header[1]
            methods = await client_reader.read(nmethods)
            if NO_AUTH not in methods: raise ConnectionAbortedError("No auth not supported")
            client_writer.write(bytes([SOCKS_VERSION, NO_AUTH])); await client_writer.drain()
            request_header = await client_reader.read(4)
            _ver, cmd, _rsv, atyp = request_header
            if cmd != CMD_CONNECT: raise ConnectionAbortedError("Unsupported command")
            if atyp == ATYP_IPV4:
                dest_addr = socket.inet_ntoa(await client_reader.read(4))
            elif atyp == ATYP_DOMAIN:
                domain_len = (await client_reader.read(1))[0]
                dest_addr = (await client_reader.read(domain_len)).decode('utf-8')
            else:
                raise ConnectionAbortedError("Unsupported address type")
            dest_port = int.from_bytes(await client_reader.read(2), 'big')
            # === End Handshake ===

            remote_reader, remote_writer, iface_name_used = await self.connect_using_best_interface(dest_addr, dest_port)

            if remote_writer is None:
                logging.error(f"All interfaces failed to connect to {dest_addr}:{dest_port}")
                client_writer.write(b'\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00') # Host unreachable
                return

            # Increment connection counter for the used interface
            if iface_name_used:
                async with self.conn_counter_lock:
                    connection_counts[iface_name_used] += 1

            bind_address = remote_writer.get_extra_info('sockname')
            reply = b'\x05\x00\x00\x01' + socket.inet_aton(bind_address[0]) + bind_address[1].to_bytes(2, 'big')
            client_writer.write(reply)
            await client_writer.drain()

            task_to_remote = asyncio.create_task(forward_data(client_reader, remote_writer, "client->remote"))
            task_from_remote = asyncio.create_task(forward_data(remote_reader, client_writer, "remote->client"))
            await asyncio.gather(task_to_remote, task_from_remote)

        except (ConnectionAbortedError, ConnectionResetError, asyncio.IncompleteReadError) as e:
            logging.warning(f"Connection issue with {client_addr}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error with {client_addr}: {e}", exc_info=True)
        finally:
            if iface_name_used:
                async with self.conn_counter_lock:
                    connection_counts[iface_name_used] -= 1
            if remote_writer:
                remote_writer.close()
            client_writer.close()
            logging.info(f"Closed connection with {client_addr}")

    async def connect_using_best_interface(self, dest_addr, dest_port):
        """Connects to a destination by trying interfaces in order of their last known latency."""
        if not self.interfaces:
            try:
                logging.info(f"Routing {dest_addr}:{dest_port} via default interface")
                reader, writer = await asyncio.open_connection(dest_addr, dest_port)
                return reader, writer, "default"
            except Exception:
                return None, None, None

        sorted_interfaces = sorted(interface_latency.items(), key=lambda item: item[1])

        for iface_name, latency in sorted_interfaces:
            local_ip = self.interfaces.get(iface_name)
            if not local_ip: continue

            logging.info(f"Attempting connection to {dest_addr}:{dest_port} via {iface_name} (last latency: {latency:.2f}ms)")
            try:
                local_addr = (local_ip, 0)
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(dest_addr, dest_port, local_addr=local_addr),
                    timeout=5
                )
                return reader, writer, iface_name
            except (OSError, asyncio.TimeoutError) as e:
                logging.warning(f"Connection via {iface_name} failed: {e}. Trying next interface.")
                interface_latency[iface_name] = 9999
                continue

        logging.error(f"All available interfaces failed to connect to {dest_addr}:{dest_port}.")
        return None, None, None

    async def start(self):
        if self.health_checker:
            self.health_checker_task = asyncio.create_task(self.health_checker.run())

        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = self.server.sockets[0].getsockname()
        logging.info(f"SOCKS5 proxy listening on {addr}")
        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        if self.health_checker:
            self.health_checker.stop()
            if self.health_checker_task:
                await self.health_checker_task
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logging.info("SOCKS5 proxy stopped.")

import curses
from dashboard import Dashboard

async def main(stdscr):
    # This main function is wrapped by curses.wrapper to handle terminal setup/teardown
    logging.info("Initializing proxy and dashboard...")
    proxy = SocksProxy('127.0.0.1', 1080)
    dashboard = Dashboard(stdscr)

    # Run proxy server and dashboard UI concurrently
    logging.info("Starting proxy and dashboard tasks.")
    proxy_task = asyncio.create_task(proxy.start())
    dashboard_task = asyncio.create_task(dashboard.run())

    try:
        await asyncio.gather(proxy_task, dashboard_task)
    except asyncio.CancelledError:
        logging.info("Main task cancelled.")
    finally:
        # Stop related tasks
        if not proxy_task.done():
            proxy_task.cancel()
        if not dashboard_task.done():
            dashboard_task.cancel()
        await proxy.stop()


if __name__ == '__main__':
    # Setup logging to a file to not interfere with curses
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='proxy.log',
        filemode='w'
    )

    try:
        curses.wrapper(lambda stdscr: asyncio.run(main(stdscr)))
    except KeyboardInterrupt:
        logging.info("Program interrupted by user.")
    finally:
        print("Proxy shutting down.")
