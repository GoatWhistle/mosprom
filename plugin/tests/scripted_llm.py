import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True


def tool_reply(call_id, name, arguments):
    return {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
        {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]}}]}


def text_reply(text):
    return {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}]}


class ScriptedLlm(object):
    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                owner.requests.append(json.loads(self.rfile.read(length).decode("utf-8")))
                reply = owner.replies.pop(0) if owner.replies else text_reply("script exhausted")
                if callable(reply):
                    reply = reply()
                body = json.dumps(reply).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self._server = _Server(("127.0.0.1", 0), Handler)
        self.port = self._server.server_port
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
