import logging
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

# This is a conceptual placeholder for a web-based dashboard.
# A real implementation would require a proper HTML template and more robust error handling.

app = Flask(__name__)
# A secret key is required for sessions, even if we don't use them.
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# Global reference to the connection manager, to be set by the main app.
connection_manager = None

def run_web_dashboard(manager):
    """
    Sets the connection manager and runs the Flask app.

    Args:
        manager: The application's ConnectionManager instance.
    """
    global connection_manager
    connection_manager = manager
    logging.info("Starting Flask-SocketIO web server on http://127.0.0.1:5000")
    # In a real app, don't use debug mode in production.
    socketio.run(app, host='127.0.0.1', port=5000, debug=False)

@app.route('/')
def index():
    """Serves the main dashboard page."""
    # A real implementation would render a template file.
    # return render_template('index.html')
    return "<h1>Netmix Web Dashboard</h1><p>Real-time updates are pushed via WebSockets.</p>"

def background_data_emitter():
    """
    Periodically gets data from the ConnectionManager and emits it to all clients.
    """
    while True:
        if connection_manager:
            health_data = connection_manager.get_health_data()
            logging.debug("Emitting health data to web clients.")
            socketio.emit('update', health_data, namespace='/dashboard')
        socketio.sleep(2) # Use socketio.sleep for background tasks

@socketio.on('connect', namespace='/dashboard')
def on_connect():
    """Handles a new client connecting to the WebSocket."""
    logging.info("Web client connected.")
    # Start the background task only when the first client connects.
    # The `socketio.start_background_task` ensures it's managed correctly.
    if not hasattr(background_data_emitter, 'task_started') or not background_data_emitter.task_started:
        background_data_emitter.task_started = True
        socketio.start_background_task(background_data_emitter)

# To run this, the main application would need to be modified to
# start this Flask app in a separate thread or process, as Flask's
# development server is blocking.
#
# Example modification in main.py:
#
# from threading import Thread
# from netmix.ui.web_dashboard import run_web_dashboard
#
# ...
# web_thread = Thread(target=run_web_dashboard, args=(conn_manager,))
# web_thread.daemon = True
# web_thread.start()
# ...
