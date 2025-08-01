import asyncio
import curses
import logging
import statistics

class Dashboard:
    def __init__(self, stdscr, connection_manager):
        """
        Args:
            stdscr: The main window object provided by curses.wrapper.
            connection_manager: An instance of the ConnectionManager.
        """
        self.stdscr = stdscr
        self.connection_manager = connection_manager

        # Basic curses setup
        self.stdscr.nodelay(1)
        self.stdscr.timeout(1000)
        curses.curs_set(0)
        if curses.has_colors():
            curses.start_color()
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
            curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)

    def get_status_and_color(self, avg_latency):
        color = curses.A_NORMAL
        if avg_latency < 100:
            status = "GOOD"
            if curses.has_colors(): color = curses.color_pair(1)
        elif avg_latency < 1000:
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
                self.stdscr.addstr(0, 0, "Netmix Dashboard (Press 'q' to quit)", curses.A_BOLD)
                self.stdscr.addstr(2, 0, f"{'Interface':<15} {'Status':<10} {'Avg Latency':<15} {'Success %':<12} {'Fails':<8} {'Active':<8}")
                self.stdscr.addstr(3, 0, "="*75)

                # Get latest data from the ConnectionManager
                health_data = self.connection_manager.get_health_data()
                row = 4

                for name, data in health_data.items():
                    if not data['latencies']:
                        avg_latency = 9999
                    else:
                        avg_latency = statistics.mean(data['latencies'])

                    successes = data['successes']
                    failures = data['failures']
                    total = successes + failures
                    success_rate = (successes / total * 100) if total > 0 else 100
                    active_conns = data['active_conns']

                    status, color = self.get_status_and_color(avg_latency)

                    self.stdscr.addstr(row, 0, f"{name:<15}")
                    self.stdscr.addstr(row, 16, f"{status:<10}", color)
                    self.stdscr.addstr(row, 27, f"{avg_latency:<15.2f}")
                    self.stdscr.addstr(row, 43, f"{success_rate:<12.1f}%")
                    self.stdscr.addstr(row, 56, f"{failures:<8}")
                    self.stdscr.addstr(row, 64, f"{active_conns:<8}")
                    row += 1

                self.stdscr.refresh()
            except curses.error as e:
                logging.warning(f"Curses error: {e}")
            except Exception as e:
                logging.error(f"Dashboard crashed: {e}", exc_info=True)
                break

            if self.stdscr.getch() == ord('q'):
                break

            await asyncio.sleep(1)
