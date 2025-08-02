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
