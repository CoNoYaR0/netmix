import asyncio
import socket
import logging

SOCKS_VERSION = 5

async def forward_data(reader, writer, direction, connection_manager, interface_name):
    """
    Reads data from a reader, writes it to a writer, and reports bandwidth usage.
    """
    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break

            num_bytes = len(data)
            if direction == 'client->remote':
                await connection_manager.record_bytes_sent(interface_name, num_bytes)
            else:  # remote->client
                await connection_manager.record_bytes_received(interface_name, num_bytes)

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
                forward_data(client_reader, remote_writer, "client->remote", self.connection_manager, iface_name_used),
                forward_data(remote_reader, client_writer, "remote->client", self.connection_manager, iface_name_used)
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
