import logging
from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import time

# This is a conceptual placeholder for a web-based dashboard.
# A real implementation would require a proper HTML template and more robust error handling.

app = Flask(__name__, template_folder='templates')
# A secret key is required for sessions, even if we don't use them.
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode='threading')

# Global references, to be set by the main app.
connection_manager = None
zerotier_manager = None

def run_web_dashboard(conn_manager, zt_manager, host='127.0.0.1', port=5000):
    """
    Sets the managers and runs the Flask app.
    """
    global connection_manager, zerotier_manager
    connection_manager = conn_manager
    zerotier_manager = zt_manager

    # Start the background data emitter thread
    emitter_thread = threading.Thread(target=background_data_emitter, daemon=True)
    emitter_thread.start()

    logging.info(f"Starting Flask-SocketIO web server on http://{host}:{port}")
    socketio.run(app, host=host, port=port, debug=False, allow_unsafe_werkzeug=True)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    return render_template('index.html')

def background_data_emitter():
    """
    Periodically gets data from the managers and emits it to all clients.
    """
    while True:
        payload = {}
        if connection_manager:
            health_data = connection_manager.get_health_data()
            # Convert deque to list for JSON serialization
            for iface in health_data:
                health_data[iface]['latencies'] = list(health_data[iface]['latencies'])
            payload['health_data'] = health_data

        if zerotier_manager:
            payload['zerotier_data'] = {
                'status': zerotier_manager.get_status(),
                'networks': zerotier_manager.list_networks()
            }

        logging.debug("Emitting data to web clients.")
        socketio.emit('update', payload, namespace='/dashboard')
        time.sleep(2)

@socketio.on('connect', namespace='/dashboard')
def on_connect():
    """Handles a new client connecting to the WebSocket."""
    logging.info("Web client connected.")
