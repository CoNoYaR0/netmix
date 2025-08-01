import asyncio
import logging
import threading
import curses

from netmix.core.interface_manager import get_active_interfaces
from netmix.core.connection_manager import ConnectionManager
from netmix.agent.ai_predictor import AIPredictor
from netmix.core.socks_proxy import SocksProxy
from netmix.ui.web_dashboard import run_web_dashboard
from netmix.core.zerotier_manager import ZeroTierManager

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
    if not interfaces:
        print("FATAL: No active network interfaces found. Cannot start.")
        return

    # --- Initialize Core Components ---
    conn_manager = ConnectionManager(interfaces)
    predictor = AIPredictor()
    proxy = SocksProxy('127.0.0.1', 1080, conn_manager, predictor)
    zt_manager = ZeroTierManager()

    # --- Start the Web Dashboard in a separate thread ---
    web_thread = threading.Thread(
        target=run_web_dashboard,
        args=(conn_manager, zt_manager),
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
