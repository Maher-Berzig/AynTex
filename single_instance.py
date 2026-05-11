# single_instance.py
"""
Single-instance guard using QLocalServer / QLocalSocket.
The first instance becomes the server. Any subsequent instance
connects to the server, forwards its command-line arguments, then exits.
"""
import sys
import json
from PyQt5.QtNetwork import QLocalServer, QLocalSocket
from PyQt5.QtCore import QObject, pyqtSignal


class SingleInstanceServer(QObject):
    """Runs in the first (primary) instance."""

    # Emitted when a second instance sends arguments (e.g. a file to open)
    args_received = pyqtSignal(list)

    def __init__(self, app_key: str, parent=None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._on_new_connection)
        self._app_key = app_key

        # Remove any leftover socket from a previous crash
        QLocalServer.removeServer(app_key)
        self._server.listen(app_key)

    def _on_new_connection(self):
        socket = self._server.nextPendingConnection()
        if not socket:
            return
        # Wait briefly for the data to arrive
        socket.waitForReadyRead(1000)
        raw = socket.readAll().data()
        socket.disconnectFromServer()
        socket.deleteLater()

        try:
            args = json.loads(raw.decode('utf-8'))
        except Exception:
            args = []

        self.args_received.emit(args)

    def close(self):
        self._server.close()


class SingleInstanceClient:
    """Tries to connect to an existing server instance."""

    def __init__(self, app_key: str):
        self._app_key = app_key

    def send_args_and_exit(self, args: list):
        """Send argv to the running instance and exit this process."""
        socket = QLocalSocket()
        socket.connectToServer(self._app_key)

        if socket.waitForConnected(1000):
            socket.write(json.dumps(args).encode('utf-8'))
            socket.flush()
            socket.waitForBytesWritten(1000)
            socket.disconnectFromServer()
        sys.exit(0)


def ensure_single_instance(app_key: str) -> SingleInstanceServer | None:
    """
    Call this AFTER creating QApplication but BEFORE showing the main window.

    Returns a SingleInstanceServer if this is the first instance (keep it alive),
    or None — but never returns in the second-instance case (calls sys.exit).
    """
    # Try to connect to an existing instance first
    socket = QLocalSocket()
    socket.connectToServer(app_key)

    if socket.waitForConnected(500):
        # Another instance is already running — forward our args and quit
        socket.write(json.dumps(sys.argv[1:]).encode('utf-8'))
        socket.flush()
        socket.waitForBytesWritten(1000)
        socket.disconnectFromServer()
        sys.exit(0)          # ← second instance dies here

    # No server found — we ARE the first instance, become the server
    return SingleInstanceServer(app_key)