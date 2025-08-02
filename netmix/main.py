import asyncio
import logging
import os
import threading
import time

from netmix.core.interface_manager import get_active_interfaces, get_interface_name_by_ip
from netmix.core.connection_manager import ConnectionManager
from netmix.agent.ai_predictor import AIPredictor
from netmix.core.socks_proxy import SocksProxy
from netmix.ui.web_dashboard import run_web_dashboard
from netmix.agent.zerotier_api import ZeroTierAPI

async def main_async(conn_manager, predictor, proxy):
    """The main asynchronous entry point for the application."""
    logging.info("Starting background tasks (health checks, proxy)...")

    manager_task = asyncio.create_task(conn_manager.run_health_checks())
    proxy_task = asyncio.create_task(proxy.start())

    try:
        await asyncio.gather(manager_task, proxy_task)
    except asyncio.CancelledError:
        logging.info("Main async task cancelled.")
    finally:
        logging.info("Shutting down async components...")
        conn_manager.stop_health_checks()
        for task in [manager_task, proxy_task]:
            if task and not task.done():
                task.cancel()
        await asyncio.sleep(0.1)

def main_sync():
    """The main synchronous entry point that sets up and runs the application."""
    # Setup logging to a file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='netmix.log',
        filemode='w'
    )

    logging.info("Initializing netmix...")
    interfaces = get_active_interfaces()

    # --- Initialize ZeroTier and discover its virtual interface ---
    zt_api = None  # Define zt_api here to have it in scope for the web dashboard
    try:
        zt_api = ZeroTierAPI()
        network_to_join = os.getenv('ZEROTIER_NETWORK_ID')

        if network_to_join:
            logging.info(f"Attempting to join configured ZeroTier network: {network_to_join}")
            try:
                zt_api.join_network(network_to_join)
                logging.info(f"Successfully sent request to join network {network_to_join}.")

                # Give the OS a moment to bring the interface up
                logging.info("Waiting for ZeroTier interface to come online...")
                time.sleep(3)  # A small delay to ensure the IP is assigned

                zt_ip = zt_api.get_virtual_ip(network_to_join)
                if zt_ip:
                    logging.info(f"Discovered ZeroTier virtual IP: {zt_ip}")
                    zt_name = get_interface_name_by_ip(zt_ip)
                    if zt_name:
                        logging.info(f"Discovered ZeroTier interface name: {zt_name}")
                        interfaces[zt_name] = zt_ip
                    else:
                        logging.warning(f"Could not find interface name for ZeroTier IP {zt_ip}. The virtual adapter will not be monitored.")
                else:
                    logging.warning("Could not get a virtual IP from ZeroTier. The virtual adapter will not be monitored.")

            except Exception as join_error:
                logging.error(f"Failed to join network {network_to_join}: {join_error}")

    except Exception as e:
        logging.error(f"Failed to initialize ZeroTier API: {e}. Continuing without it.")
        # zt_api is already None

    if not interfaces:
        print("FATAL: No active network interfaces found (including ZeroTier). Cannot start.")
        logging.error("FATAL: No active network interfaces found (including ZeroTier). Cannot start.")
        return

    # --- Initialize Core Components with all interfaces ---
    conn_manager = ConnectionManager(interfaces)
    predictor = AIPredictor()
    proxy = SocksProxy('127.0.0.1', 1080, conn_manager, predictor)

    # --- Start the Web Dashboard in a separate thread ---
    web_thread = threading.Thread(
        target=run_web_dashboard,
        args=(conn_manager, zt_api),
        daemon=True
    )
    web_thread.start()

    # --- Start the main asyncio application ---
    try:
        asyncio.run(main_async(conn_manager, predictor, proxy))
    except KeyboardInterrupt:
        logging.info("Program interrupted by user.")
    finally:
        print("Netmix has shut down. Check netmix.log for details.")

if __name__ == '__main__':
    main_sync()
