import hmac
import json
import mimetypes
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, quote, unquote, urlparse

from ..chat.files import MAX_ATTACHMENT_BYTES
from ..protocol.local_mcp import LOOPBACK_HOSTS, _host_of, new_token
from .bridge import BridgeError

MAX_JSON_BODY = 1024 * 1024
POLL_SECONDS = 25.0
TOKEN_HEADER = "X-Brim-Token"
STATIC_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
                ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
                ".ico": "image/x-icon"}


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        if not isinstance(sys.exc_info()[1], ConnectionError):
            HTTPServer.handle_error(self, request, client_address)


class WebChatServer(object):
    def __init__(self, bridge, web_dir, port=0, token=None):
        self._bridge = bridge
        self._web_dir = os.path.realpath(web_dir)
        self._port = port
        self._token = token or new_token()
        self._server = None

    def port(self):
        return self._server.server_port if self._server is not None else None

    def url(self):
        if self._server is None:
            return None
        return "http://127.0.0.1:%d/?token=%s" % (self.port(), self._token)

    def _token_ok(self, value):
        return hmac.compare_digest((value or "").encode("utf-8"), self._token.encode("utf-8"))

    def start(self):
        if self._server is not None:
            return self.port()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *args):
                return

            def _send(self, status, body, content_type, extra=None):
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                for name, value in (extra or {}).items():
                    self.send_header(name, value)
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(body)

            def _json(self, status, payload):
                self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                           "application/json; charset=utf-8")

            def _raw_json(self, status, text):
                self._send(status, text.encode("utf-8"), "application/json; charset=utf-8")

            def _loopback(self):
                if _host_of(self.headers.get("Host")) in LOOPBACK_HOSTS:
                    return True
                self._json(403, {"error": "loopback host required"})
                return False

            def _authorized(self, query):
                if owner._token_ok(self.headers.get(TOKEN_HEADER) or (query.get("token") or [""])[0]):
                    return True
                self._json(401, {"error": "unauthorized"})
                return False

            def _length(self, limit):
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    length = -1
                if length < 0 or length > limit:
                    self._json(413, {"error": "body too large"})
                    self.close_connection = True
                    return None
                return length

            def _body(self):
                length = self._length(MAX_JSON_BODY)
                if length is None:
                    return None
                try:
                    payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
                except ValueError:
                    payload = None
                if not isinstance(payload, dict):
                    self._json(400, {"error": "JSON object expected"})
                    return None
                return payload

            def _guard(self, action):
                try:
                    action()
                except BridgeError as error:
                    self._json(error.status, {"error": str(error)})

            def do_GET(self):
                if not self._loopback():
                    return
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                if parsed.path == "/api/view":
                    if self._authorized(query):
                        self._guard(lambda: self._view(query))
                elif parsed.path == "/api/download":
                    if self._authorized(query):
                        self._guard(lambda: self._download(query))
                else:
                    self._static(parsed.path)

            do_HEAD = do_GET

            def do_POST(self):
                if not self._loopback():
                    return
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                if not self._authorized(query):
                    self.close_connection = True
                    return
                if parsed.path == "/api/action":
                    payload = self._body()
                    if payload is not None:
                        self._guard(lambda: self._json(200, {"result": owner._bridge.act(payload.get("name"),
                                                                                          payload.get("args"))}))
                elif parsed.path == "/api/open":
                    payload = self._body()
                    if payload is not None:
                        self._guard(lambda: self._json(200, {"result": owner._bridge.open_path(payload.get("path"))}))
                elif parsed.path == "/api/upload":
                    length = self._length(MAX_ATTACHMENT_BYTES)
                    if length is not None:
                        name = (query.get("name") or [""])[0]
                        self._guard(lambda: self._json(200, {"path": owner._bridge.upload(name, self.rfile, length)}))
                else:
                    self.close_connection = True
                    self._json(404, {"error": "not found"})

            def _view(self, query):
                try:
                    since = int((query.get("since") or ["-1"])[0])
                except ValueError:
                    since = -1
                version, encoded = owner._bridge.snapshot(since, POLL_SECONDS)
                if encoded is None:
                    self._json(503, {"error": "chat is starting"})
                    return
                self._raw_json(200, '{"version": %d, "view": %s}' % (version, encoded))

            def _download(self, query):
                path = owner._bridge.readable((query.get("path") or [""])[0])
                with open(path, "rb") as handle:
                    body = handle.read()
                name = os.path.basename(path)
                self._send(200, body, "application/octet-stream",
                           {"Content-Disposition": "attachment; filename*=UTF-8''%s" % quote(name)})

            def _static(self, path):
                relative = unquote(path).lstrip("/") or "index.html"
                target = os.path.realpath(os.path.join(owner._web_dir, relative))
                if not target.startswith(owner._web_dir + os.sep) or not os.path.isfile(target):
                    self._json(404, {"error": "not found"})
                    return
                extension = os.path.splitext(target)[1].lower()
                content_type = STATIC_TYPES.get(extension) or mimetypes.guess_type(target)[0] or "application/octet-stream"
                with open(target, "rb") as handle:
                    body = handle.read()
                self._send(200, body, content_type, {"Referrer-Policy": "no-referrer"})

        self._server = _Server(("127.0.0.1", self._port), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self.port()

    def stop(self):
        server, self._server = self._server, None
        if server is not None:
            server.shutdown()
            server.server_close()
