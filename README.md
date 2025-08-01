# Multipath SOCKS5 Proxy

This project is a Python-based SOCKS5 proxy designed for Windows that provides intelligent, local multipath routing over multiple network interfaces (e.g., Wi-Fi and 4G/LTE). It aims to improve network resilience and performance by dynamically routing traffic based on interface health.

## Features

- **SOCKS5 Compliant:** Acts as a standard SOCKS5 proxy, compatible with most network applications.
- **Dynamic Interface Detection:** Automatically discovers all active, non-loopback network interfaces on startup.
- **Latency-Based Routing:** The proxy periodically checks the latency of each interface by connecting to a reliable host. New connections are routed through the interface with the currently lowest latency.
- **Automatic Failover:** If a connection attempt on the best interface fails, it is marked as "down" (given a high latency penalty), and the proxy instantly retries the connection on the next-best interface.
- **Live CLI Dashboard:** An integrated, real-time command-line dashboard (built with `curses`) displays the status, current latency, and active connection count for each interface.

## Prerequisites

- Python 3.7+
- `pip` for installing dependencies

## Installation

1.  Clone the repository or download the source code.
2.  Navigate to the project's root directory.
3.  Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```

## How to Run

To run the proxy and the monitoring dashboard, execute the main script from the root directory:

```sh
python3 src/socks_proxy.py
```

- The proxy server will start listening on `127.0.0.1:1080`.
- The terminal will display the live monitoring dashboard.
- All log messages from the proxy are written to `proxy.log` in the root directory to avoid interfering with the dashboard UI.

To use the proxy, configure your application's SOCKS5 proxy settings to point to `127.0.0.1` on port `1080`.

## Using the Dashboard

The dashboard will start automatically when you run the proxy.

- It displays each detected network interface, its status (`GOOD`, `DEGRADED`, `DOWN`), its last measured latency in milliseconds, and the number of currently active connections being routed through it.
- To exit the proxy and the dashboard, press **`q`**.
