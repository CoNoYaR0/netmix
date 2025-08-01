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
> **Note:** The `requirements.txt` file includes `windows-curses`, which is necessary for the dashboard to run on Windows. This dependency is installed only on Windows systems.

## How to Run

To run the proxy and the monitoring dashboard, execute the main script **from the project's root directory** using Python's `-m` flag to ensure the package is loaded correctly:

```sh
python -m netmix.main
```
(Use `python3` if that is your default interpreter)

- The proxy server will start listening on `127.0.0.1:1080`.
- The proxy server will start listening on `127.0.0.1:1080`.
- The web dashboard will be available at **http://127.0.0.1:5000**.
- All log messages are written to `netmix.log` in the root directory.

To use the proxy, configure your application's SOCKS5 proxy settings to point to `127.0.0.1` on port `1080`.

## Using the Web Dashboard

Once you run the application, open your web browser and navigate to **http://127.0.0.1:5000**.

- The dashboard provides a real-time view of each detected network interface.
- It displays the status (`GOOD`, `DEGRADED`, `DOWN`), average latency, success rate, failure counts, and the number of active connections for each interface.
- The data updates automatically via WebSockets.
- To stop the entire application, press **`Ctrl+C`** in the terminal where it is running.

## AI-Based Routing and Training

The proxy uses a prediction agent (`netmix/agent/ai_predictor.py`) to choose the best interface. By default, it uses a simple heuristic. However, you can train a proper machine learning model for more intelligent routing.

1.  **Data Collection:** As you run `netmix`, it will automatically log health and performance data for your interfaces into a `netmix_training_data.csv` file. Let the application run for a while under normal usage to collect a good dataset.
2.  **Training the Model:** Once you have collected enough data, you can run the training script:
    ```sh
    python -m netmix.agent.train
    ```
    This will use the CSV data to train a RandomForest model and save it as `model.joblib`.
3.  **Automatic Usage:** The next time you start `netmix`, it will automatically detect and load `model.joblib` and use it for predictions. If `model.joblib` is not found, it will revert to the default heuristic.

## Building the Executable

This project can be packaged into a single standalone executable for Windows using PyInstaller.

1.  Ensure you have PyInstaller installed: `pip install pyinstaller`.
2.  Run the build command from the root directory:
    ```sh
    pyinstaller netmix.spec
    ```
3.  The final `netmix.exe` file will be located in the `dist/netmix` directory.
