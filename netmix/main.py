import asyncio
import socket
import logging
from netmix.core.interface_manager import get_active_interfaces
from netmix.core.connection_manager import ConnectionManager
from netmix.agent.ai_predictor import AIPredictor

SOCKS_VERSION = 5

async def forward_data(reader, writer, direction):
    """Reads data from a reader and writes it to a writer, effectively proxying the stream."""
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
    def __init__(self, host, port, connection_manager, predictor):
        self.host = host
        self.port = port
        self.connection_manager = connection_manager
        self.predictor = predictor
        self.server = None

    async def handle_client(self, client_reader, client_writer):
        client_addr = client_writer.get_extra_info('peername')
        logging.info(f"New connection from {client_addr}")

        remote_writer = None
        iface_name_used = None
        try:
            # --- SOCKS5 Handshake ---
            header = await client_reader.read(2)
            if not header or header[0] != SOCKS_VERSION: raise ConnectionAbortedError("Bad SOCKS version")
            nmethods = header[1]
            methods = await client_reader.read(nmethods)
            if 0x00 not in methods: raise ConnectionAbortedError("No auth not supported")
            client_writer.write(bytes([SOCKS_VERSION, 0x00])); await client_writer.drain()

            request_header = await client_reader.read(4)
            _ver, cmd, _rsv, atyp = request_header
            if cmd != 1: raise ConnectionAbortedError("Unsupported command")

            if atyp == 1: # IPv4
                dest_addr = socket.inet_ntoa(await client_reader.read(4))
            elif atyp == 3: # Domain
                domain_len = (await client_reader.read(1))[0]
                dest_addr = (await client_reader.read(domain_len)).decode('utf-8')
            else: raise ConnectionAbortedError("Unsupported address type")
            dest_port = int.from_bytes(await client_reader.read(2), 'big')
            # --- End Handshake ---

            remote_reader, remote_writer, iface_name_used = await self.connect_to_destination(dest_addr, dest_port)

            if remote_writer is None:
                logging.error(f"All interfaces failed to connect to {dest_addr}:{dest_port}")
                client_writer.write(b'\x05\x04\x00\x01\x00\x00\x00\x00\x00\x00') # Host unreachable
                return

            await self.connection_manager.increment_active_conn(iface_name_used)

            bind_address = remote_writer.get_extra_info('sockname')
            reply = b'\x05\x00\x00\x01' + socket.inet_aton(bind_address[0]) + bind_address[1].to_bytes(2, 'big')
            client_writer.write(reply); await client_writer.drain()

            await asyncio.gather(
                forward_data(client_reader, remote_writer, "client->remote"),
                forward_data(remote_reader, client_writer, "remote->client")
            )

        except (ConnectionAbortedError, ConnectionResetError, asyncio.IncompleteReadError) as e:
            logging.warning(f"Connection issue with {client_addr}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error with {client_addr}: {e}", exc_info=True)
        finally:
            if iface_name_used:
                await self.connection_manager.decrement_active_conn(iface_name_used)
            if remote_writer: remote_writer.close()
            client_writer.close()
            logging.info(f"Closed connection with {client_addr}")

    async def connect_to_destination(self, dest_addr, dest_port):
        """
        Uses the AI predictor to choose an interface and attempts to connect.
        Records successes and failures with the ConnectionManager.
        """
        health_data = self.connection_manager.get_health_data()
        attempt_data = dict(health_data)

        for _ in range(len(self.connection_manager.interfaces)):
            iface_name = self.predictor.predict_best_interface(attempt_data)
            if not iface_name:
                logging.error("AI Predictor returned no interface.")
                break

            local_ip = self.connection_manager.interfaces.get(iface_name)
            logging.info(f"Attempting connection to {dest_addr}:{dest_port} via predicted interface '{iface_name}'")
            try:
                local_addr = (local_ip, 0)
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(dest_addr, dest_port, local_addr=local_addr),
                    timeout=5
                )
                await self.connection_manager.record_success(iface_name)
                return reader, writer, iface_name
            except (OSError, asyncio.TimeoutError) as e:
                logging.warning(f"Connection via {iface_name} failed: {e}. Recording failure.")
                await self.connection_manager.record_failure(iface_name)
                attempt_data[iface_name]['failures'] += 1
                continue

        logging.error(f"All available interfaces failed to connect to {dest_addr}:{dest_port}.")
        return None, None, None

    async def start(self):
        self.server = await asyncio.start_server(self.handle_client, self.host, self.port)
        addr = self.server.sockets[0].getsockname()
        logging.info(f"SOCKS5 proxy listening on {addr}")
        async with self.server:
            await self.server.serve_forever()

# This __main__ block will be moved to a main.py later
if __name__ == '__main__':
    import curses
    from netmix.ui.dashboard import Dashboard

    async def main(stdscr):
        logging.info("Initializing netmix...")

        interfaces = get_active_interfaces()
        if not interfaces:
            print("Error: No active network interfaces found. Exiting.")
            return

        conn_manager = ConnectionManager(interfaces)
        predictor = AIPredictor()
        proxy = SocksProxy('127.0.0.1', 1080, conn_manager, predictor)
        dashboard = Dashboard(stdscr, conn_manager)

        logging.info("Starting background tasks (health checks, proxy, dashboard)...")
        manager_task = asyncio.create_task(conn_manager.run_health_checks())
        proxy_task = asyncio.create_task(proxy.start())
        dashboard_task = asyncio.create_task(dashboard.run())

        try:
            await asyncio.gather(manager_task, proxy_task, dashboard_task)
        except asyncio.CancelledError:
            logging.info("Main task cancelled.")
        finally:
            logging.info("Shutting down...")
            conn_manager.stop_health_checks()
            for task in [manager_task, proxy_task, dashboard_task]:
                if not task.done():
                    task.cancel()
            await asyncio.sleep(0.1) # Allow tasks to process cancellation

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        filename='proxy.log',
        filemode='w'
    )

    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        logging.info("Program interrupted by user.")
    finally:
        print("Netmix has shut down.")
