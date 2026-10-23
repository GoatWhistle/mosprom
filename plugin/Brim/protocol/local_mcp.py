import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "[::1]")
MAX_BODY = 1024 * 1024


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def new_token():
    return os.urandom(24).hex()


def _host_of(header):
    value = (header or "").strip().lower()
    if value.startswith("["):
        return value.split("]")[0] + "]"
    return value.split(":")[0]


class LocalMcpServer(object):
    def __init__(self, dispatcher, token=None, port=0):
        self._dispatcher = dispatcher
        self._token = token or new_token()
        self._port = port
        self._server = None
        self._thread = None

    def token(self):
        return self._token

    def port(self):
        return self._server.server_port if self._server is not None else None

    def start(self):
        if self._server is not None:
            return self.port()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                return

            def _reply(self, status, payload=None):
                body = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _authorized(self):
                if _host_of(self.headers.get("Host")) not in LOOPBACK_HOSTS:
                    return False
                if self.headers.get("Origin"):
                    return False
                header = self.headers.get("Authorization") or ""
                prefix = "Bearer "
                if not header.startswith(prefix):
                    return False
                return hmac.compare_digest(header[len(prefix):].encode("utf-8"), owner._token.encode("utf-8"))

            def do_POST(self):
                if not self._authorized():
                    self._reply(401, {"error": "unauthorized"})
                    return
                if self.path.split("?")[0] != "/mcp":
                    self._reply(404, {"error": "not found"})
                    return
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    length = -1
                if length < 0 or length > MAX_BODY:
                    self._reply(413, {"error": "body too large"})
                    return
                response = owner._dispatcher.handle_text(self.rfile.read(length))
                if response is None:
                    self.send_response(202)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self._reply(200, response)

            def do_GET(self):
                self._reply(405, {"error": "use POST /mcp"})

        self._server = _Server(("127.0.0.1", self._port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self.port()

    def stop(self):
        server, self._server = self._server, None
        if server is not None:
            server.shutdown()
            server.server_close()
