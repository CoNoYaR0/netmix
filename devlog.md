# Developer Log

This document chronicles the development process and key architectural decisions for the `netmix` project.

## 2025-08-01: Phase 1 - SOCKS5 Multipath Proxy MVP

The initial phase of the project focused on building a Minimum Viable Product for a local multipath SOCKS5 proxy on Windows.

### Key Accomplishments:
- **SOCKS5 Server:** A fully compliant SOCKS5 proxy was built using Python's `asyncio` library for high-performance I/O.
- **Dynamic Interface Discovery:** The proxy uses the `psutil` library to automatically detect all active, non-loopback network interfaces at startup.
- **Round-Robin Routing:** The initial routing strategy was a simple round-robin scheduler, distributing new connections evenly across all available interfaces.
- **Reactive Failover:** A robust failover mechanism was implemented. If a connection on a given interface failed, the proxy would remove that interface from the active pool and retry on another, ensuring resilience.
- **Latency-Based Routing:** The routing logic was enhanced to use a background `HealthChecker` task. This task periodically measures the latency of each interface, allowing the proxy to route new connections through the fastest one.
- **CLI Dashboard:** A real-time dashboard was created using the `curses` library to monitor the status, latency, and active connection count of each interface.
- **Windows Compatibility:** Addressed a key Windows issue by adding the `windows-curses` dependency to ensure the dashboard runs correctly on the target OS.

### Outcome:
Phase 1 resulted in a functional, intelligent SOCKS5 proxy that successfully balances load and handles network failures. This strong foundation serves as the starting point for the expanded `netmix` vision.

## 2025-08-01: Phase 2 - Architecture and Web UI

With the core proxy functionality in place, the project was restructured for greater extensibility and the user interface was upgraded.

### Key Accomplishments:
- **Repository Restructure:** The project was reorganized into a `netmix` package with `core`, `ui`, and `agent` submodules to create a cleaner architecture.
- **Connection Manager:** The `HealthChecker` was evolved into a comprehensive `ConnectionManager`, which now acts as the central source of truth for all network health statistics, including latency history and connection success/failure rates.
- **Web Dashboard:** The `curses`-based CLI dashboard was replaced with a new web-based dashboard built with Flask and Flask-SocketIO. This provides a more robust and user-friendly interface, accessible at http://127.0.0.1:5000, which updates in real-time via WebSockets.
- **ML-Powered Routing:** A full pipeline for optional machine learning-based routing was implemented. The `ConnectionManager` logs training data, a `train.py` script builds a model, and the `AIPredictor` uses the trained model if available.
- **Packaging:** A `netmix.spec` file was created to allow for easy packaging of the entire application into a standalone Windows executable using PyInstaller.
- **ZeroTier API Integration:** The initial `zerotier-cli` wrapper was replaced with a much more robust `ZeroTierAPI` agent that communicates directly with the ZeroTier One local REST API, removing PATH dependencies and improving stability.

### Post-Phase 2 Bug Fixes
- **Corrected Project Structure:** Fixed a `ModuleNotFoundError` by properly separating the main application runner (`main.py`) from the SOCKS proxy class definition (`core/socks_proxy.py`).
- **Fixed `curses` and `asyncio` Integration:** Resolved a `RuntimeWarning` by implementing a synchronous wrapper function to correctly launch the asyncio event loop from the `curses` library.
- **Fixed JSON Serialization:** Resolved a `TypeError` in the web dashboard by converting `collections.deque` objects to `lists` before emitting them over WebSockets.
- **Robust ZeroTier Discovery:** Hardened the `ZeroTierAPI` agent against `FileNotFoundError` by improving the auto-detection logic for the `zerotier-cli` executable and then replacing it entirely with a direct API client to avoid PATH issues.

## 2025-08-01: Phase 3 - Network Bonding and Advanced Features

This phase begins the work on the most advanced features, starting with the foundational step of connecting to a virtual network to enable future bonding experiments.

### Key Accomplishments:
- **ZeroTier Auto-Join:** The application can now be configured with a `ZEROTIER_NETWORK_ID` in the `.env` file. On startup, it will automatically send a request to join this network, enabling persistent virtual network presence.

### Post-Phase 2 Stability Fixes:
- **`NameError` Resolution:** A persistent `NameError` related to the `os` module in the ZeroTier API agent was definitively resolved by recreating the file to ensure a clean state, fixing a critical initialization bug.
- **Final Validation:** The application is now stable, with all components (Proxy, Connection Manager, AI Predictor, Web Dashboard, and ZeroTier Agent) initializing and running correctly.

### Phase 3 Follow-Up: Full Integration and Stability

Following the initial auto-join feature, this work fully integrates the ZeroTier virtual adapter into the application's core logic and resolves several stability and usability issues.

#### Key Accomplishments (2025-08-01):
- **Full ZeroTier Adapter Integration:** The ZeroTier virtual network adapter is now treated as a first-class citizen. The application startup sequence was re-engineered to detect the virtual IP and interface name after joining a network, and this interface is now passed to the `ConnectionManager` for monitoring.
- **Dashboard Enhancements:** The web dashboard now features a dedicated panel showing the real-time status of the managed ZeroTier network, including its ID, status, and assigned virtual IP. A bug was also fixed to prevent `(undefined)` from appearing if a network has no display name.
- **Robust Health Checks:** The `ConnectionManager`'s health check for the ZeroTier adapter is now more reliable. It dynamically finds the network's default gateway and uses that for latency checks, removing the dependency on public internet access and providing a more accurate measure of the virtual link's health.
- **Dependency & Stability Fixes:** Refactored the `AIPredictor` to remove a dependency on the `pandas` library, resolving a critical startup crash. Also removed a lingering and unused `curses` import to improve stability and cross-platform compatibility.
