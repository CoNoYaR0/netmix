import logging
import os
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
zerotier_api = None

def run_web_dashboard(conn_manager, zt_api, host='127.0.0.1', port=5000):
    """
    Sets the managers and runs the Flask app.
    """
    global connection_manager, zerotier_api
    connection_manager = conn_manager
    zerotier_api = zt_api

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

        if zerotier_api:
            try:
                managed_network_id = os.getenv('ZEROTIER_NETWORK_ID')
                managed_network_details = None
                if managed_network_id:
                    try:
                        # This call might fail if the node hasn't fully joined yet
                        managed_network_details = zerotier_api.get_network(managed_network_id)
                    except Exception:
                        managed_network_details = {
                            'id': managed_network_id,
                            'status': 'NOT_FOUND',
                            'error': 'Network details not yet available. May be connecting.'
                        }

                payload['zerotier_data'] = {
                    'status': zerotier_api.get_status(),
                    'managed_network': managed_network_details
                }
            except Exception as e:
                logging.error(f"Could not fetch ZeroTier data for dashboard: {e}")
                payload['zerotier_data'] = {'error': str(e)}

        logging.debug("Emitting data to web clients.")
        socketio.emit('update', payload, namespace='/dashboard')
        time.sleep(2)

@socketio.on('connect', namespace='/dashboard')
def on_connect():
    """Handles a new client connecting to the WebSocket."""
    logging.info("Web client connected.")
