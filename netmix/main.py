import asyncio
import logging
import threading
from netmix.core.interface_manager import get_active_interfaces
from netmix.core.connection_manager import ConnectionManager
from netmix.agent.ai_predictor import AIPredictor
from netmix.core.socks_proxy import SocksProxy
from netmix.ui.web_dashboard import run_web_dashboard
from netmix.core.zerotier_manager import ZeroTierManager

async def main_async():
    """The main asynchronous entry point for the application."""
    logging.info("Initializing netmix components...")

    interfaces = get_active_interfaces()
    if not interfaces:
        logging.critical("Error: No active network interfaces found. Exiting.")
        return

    # Initialize the core components
    conn_manager = ConnectionManager(interfaces)
    predictor = AIPredictor()
    proxy = SocksProxy('127.0.0.1', 1080, conn_manager, predictor)

    # --- Start Background Tasks ---
    # Start the ConnectionManager's health checks
    manager_task = asyncio.create_task(conn_manager.run_health_checks())

    # Start the SOCKS5 proxy server
    proxy_task = asyncio.create_task(proxy.start())

    logging.info("All background tasks started.")

    try:
        # Keep the async part of the application running
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

if __name__ == '__main__':
    # Setup logging to a file
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='netmix.log',
        filemode='w'
    )

    # --- Initialize Components for Web UI ---
    # The ConnectionManager needs to be accessible by the web thread.
    # We create it here, in the main thread.
    interfaces = get_active_interfaces()
    if not interfaces:
        print("FATAL: No active network interfaces found. Cannot start.")
    else:
        conn_manager_for_web = ConnectionManager(interfaces)
        zt_manager = ZeroTierManager()

        # --- Start the Web Dashboard in a separate thread ---
        web_thread = threading.Thread(
            target=run_web_dashboard,
            args=(conn_manager_for_web, zt_manager),
            daemon=True
        )
        web_thread.start()

        # --- Start the main asyncio application ---
        # We need to re-architect the async part to accept the pre-initialized conn_manager
        # For now, we will have a temporary duplication.
        # This highlights the need for a central application context object.
        # TODO: Refactor to use a single AppContext object.

        # This is a simplified async main function for the refactored structure
        async def run_async_services():
            logging.info("Initializing async services...")
            predictor = AIPredictor()
            proxy = SocksProxy('127.0.0.1', 1080, conn_manager_for_web, predictor)
            manager_task = asyncio.create_task(conn_manager_for_web.run_health_checks())
            proxy_task = asyncio.create_task(proxy.start())
            await asyncio.gather(manager_task, proxy_task)

        try:
            asyncio.run(run_async_services())
        except KeyboardInterrupt:
            logging.info("Program interrupted by user.")
        finally:
            print("Netmix has shut down. Check netmix.log for details.")
