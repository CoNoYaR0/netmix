# Netmix: An Intelligent Local Multipath Proxy

Netmix is a Python-based SOCKS5 proxy designed for Windows that provides intelligent, local multipath routing over multiple network interfaces (e.g., Wi-Fi and 4G/LTE). It aims to improve network resilience and performance by dynamically routing traffic based on interface health and, eventually, simulating true network bonding.

---

## Project Roadmap & Status

This project is being developed in phases. Here is a summary of our progress and future plans.

### ✅ Phase 1: MVP SOCKS5 Proxy (Complete)
The initial phase focused on building a functional, intelligent SOCKS5 proxy.
- **Features:** Dynamic interface discovery, latency-based routing, automatic failover, and a basic `curses` CLI dashboard.

### ✅ Phase 2: Architectural Refactor & Web UI (Complete)
This phase focused on creating a more robust and extensible application architecture.
- **Features:** Reorganized the project into a `netmix` package, created a central `ConnectionManager` for health data, implemented a placeholder `AIPredictor`, and replaced the CLI dashboard with a real-time **Web Dashboard** built with Flask and Socket.IO. The ZeroTier integration was also upgraded from a CLI wrapper to a direct **REST API client**. Numerous stability bugs were also fixed.

### 🚧 Phase 3: Network Bonding & Advanced Intelligence (In Progress)
This is the current phase, focused on implementing advanced networking features and making the application production-ready.
- **Planned Features:**
    - **True Bandwidth Aggregation:** Emulate Speedify-like bonding locally using ZeroTier or other methods.
    - **Per-Interface Traffic Shaping:** Track and manage bandwidth usage per interface.
    - **Enhanced AI Engine:** Move from a heuristic to a true ML model (XGBoost or lightweight LLM).
    - **Full Offline Mode:** Ensure the application can run without any reliance on external APIs.
    - **Packaging & Distribution:** Finalize the `.exe` package and create an auto-updater.

### Phase 4: Automatic Traffic Capture (Planned)
- **Planned Features:**
    - **Automatic System-Wide Proxy:** Implement a mechanism to automatically capture all system network traffic, removing the need for manual SOCKS5 configuration in applications. This may involve programmatically setting system proxy settings or creating a virtual network adapter.

### Phase 5: Hardening & Remote Access (Planned)
- **Planned Features:**
    - **Remote Dashboard Access:** Add optional HTTPS and authentication to the web dashboard.

---

## Prerequisites

- Python 3.7+
- `pip` for installing dependencies
- (Optional) ZeroTier One client installed, for ZeroTier status monitoring.

## Configuration

The application can be configured using a `.env` file in the root directory. Copy the `.env.example` file to `.env` to get started.

- **ZT_API:** The URL of the ZeroTier local API.
- **ZT_TOKEN:** Your ZeroTier API authentication token. If left blank, the application will attempt to read it from the default installation path on Windows.
- **ZEROTIER_NETWORK_ID:** The 16-character ID of the ZeroTier network you want to automatically join on startup.

## Installation

1.  Clone the repository or download the source code.
2.  Navigate to the project's root directory.
3.  Install the required Python packages:
    ```sh
    pip install -r requirements.txt
    ```
> **Note:** The `requirements.txt` file includes `windows-curses`, which is necessary for the dashboard to run on Windows.

## How to Run

To run the proxy and the monitoring dashboard, execute the main script **from the project's root directory** using Python's `-m` flag to ensure the package is loaded correctly:

```sh
python -m netmix.main
```
(Use `python3` if that is your default interpreter)

- The proxy server will start listening on `127.0.0.1:1080`.
- The web dashboard will be available at **http://127.0.0.1:5000**.
- All log messages are written to `netmix.log` in the root directory.

To use the proxy, configure your application's SOCKS5 proxy settings to point to `127.0.0.1` on port `1080`.

## Using the Web Dashboard

Once you run the application, open your web browser and navigate to **http://127.0.0.1:5000**.

- The dashboard provides a real-time view of each detected network interface and the ZeroTier client status.
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
