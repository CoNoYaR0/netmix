import asyncio
import curses
import logging
from health_checker import interface_latency, connection_counts

class Dashboard:
    def __init__(self, stdscr):
        """
        stdscr: The main window object provided by curses.wrapper.
        """
        self.stdscr = stdscr
        # Basic curses setup
        self.stdscr.nodelay(1) # Non-blocking getch
        self.stdscr.timeout(1000) # Timeout for getch in ms
        curses.curs_set(0) # Hide the cursor
        # Set up color pairs
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)

    def get_status_and_color(self, latency):
        color = curses.A_NORMAL
        if latency < 100:
            status = "GOOD"
            if curses.has_colors(): color = curses.color_pair(1)
        elif latency < 1000:
            status = "DEGRADED"
            if curses.has_colors(): color = curses.color_pair(2)
        else:
            status = "DOWN"
            if curses.has_colors(): color = curses.color_pair(3)
        return status, color

    async def run(self):
        """The main loop to draw the dashboard."""
        while True:
            try:
                self.stdscr.clear()

                # Header
                self.stdscr.addstr(0, 0, "Multipath Proxy Dashboard (Press 'q' to quit)", curses.A_BOLD)
                self.stdscr.addstr(2, 0, f"{'Interface':<20} {'Status':<12} {'Latency (ms)':<15} {'Active Conns':<15}")
                self.stdscr.addstr(3, 0, "="*70)

                # Interface data
                row = 4
                iface_names = list(interface_latency.keys())

                for name in iface_names:
                    latency = interface_latency.get(name, 9999)
                    conns = connection_counts.get(name, 0)
                    status, color = self.get_status_and_color(latency)

                    self.stdscr.addstr(row, 0, f"{name:<20}")
                    self.stdscr.addstr(row, 21, f"{status:<12}", color)
                    self.stdscr.addstr(row, 34, f"{latency:<15.2f}")
                    self.stdscr.addstr(row, 50, f"{conns:<15}")
                    row += 1

                self.stdscr.refresh()
            except curses.error as e:
                logging.warning(f"Curses error: {e}")

            # Check for quit command
            key = self.stdscr.getch()
            if key == ord('q'):
                break

            await asyncio.sleep(1)

async def main_dashboard_async(stdscr):
    """Async wrapper for the dashboard run method."""
    await Dashboard(stdscr).run()

if __name__ == '__main__':
    # This allows running the dashboard standalone for testing.
    # We will initialize with some dummy data.
    logging.basicConfig(level=logging.INFO)

    interface_latency['Wi-Fi'] = 55.5
    connection_counts['Wi-Fi'] = 3
    interface_latency['Ethernet'] = 9999
    connection_counts['Ethernet'] = 0

    try:
        # curses.wrapper handles terminal setup and cleanup
        curses.wrapper(lambda stdscr: asyncio.run(main_dashboard_async(stdscr)))
    except KeyboardInterrupt:
        logging.info("Dashboard stopped by user.")
