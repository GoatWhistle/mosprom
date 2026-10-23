import queue
import threading

from . import constants, frames
from .websocket_client import WebSocketClient, WebSocketError

try:
    from urllib.parse import quote
except ImportError:
    from urllib import quote


def websocket_url(backend_url, token):
    base = backend_url.rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://"):]
    return "%s%s/instances/ws?token=%s" % (base, constants.API_PREFIX, quote(token, safe=""))


def mcp_envelope(frame):
    if "method" in frame:
        envelope = dict((key, value) for key, value in frame.items() if key not in ("type", "id", "request_id"))
        envelope.setdefault("jsonrpc", "2.0")
        envelope.setdefault("id", frame.get("request_id", frame["id"]))
        return envelope
    for key in ("jsonrpc", "request", "payload"):
        if isinstance(frame.get(key), dict):
            return frame[key]
    return None


SNAPSHOT_DEBOUNCE = 0.3


class BridgeConnection(object):
    def __init__(self, settings, hello_builder, ledger, executor, dispatcher, snapshot_builder,
                 on_chat_event=None, on_status=None, on_progress=None, on_tool_result=None, authorized=None,
                 client_factory=WebSocketClient, backoff=(1.0, 2.0, 5.0, 10.0, 30.0)):
        self._settings = settings
        self._authorized = authorized
        self._on_progress = on_progress or (lambda frame: None)
        self._on_tool_result = on_tool_result or (lambda frame, tool: None)
        self._hello_builder = hello_builder
        self._ledger = ledger
        self._executor = executor
        self._dispatcher = dispatcher
        self._snapshot_builder = snapshot_builder
        self._on_chat_event = on_chat_event or (lambda frame: None)
        self._on_status = on_status or (lambda status: None)
        self._client_factory = client_factory
        self._backoff = backoff
        self._client = None
        self._stop = threading.Event()
        self._work = queue.Queue()
        self._connected = threading.Event()
        self._snapshot_due = threading.Event()
        self._threads = []

    def start(self):
        self._stop.clear()
        for target in (self._run_connection, self._run_worker, self._run_snapshots):
            thread = threading.Thread(target=target, daemon=True)
            thread.start()
            self._threads.append(thread)

    def stop(self):
        self._stop.set()
        self._work.put(None)
        self._snapshot_due.set()
        client = self._client
        if client is not None:
            client.close()

    def cancel_run(self, run_id):
        self._executor.cancel_run(run_id)

    def reconnect(self):
        client = self._client
        if client is not None:
            client.close()

    def is_connected(self):
        return self._connected.is_set()

    def send(self, frame):
        client = self._client
        if client is None or not self._connected.is_set():
            return False
        try:
            client.send_text(frames.encode_frame(frame))
            return True
        except (WebSocketError, OSError):
            self._connected.clear()
            return False

    def push_snapshot(self):
        scene_version, state = self._snapshot_builder()
        return self.send(frames.snapshot_frame(scene_version, state))

    def schedule_snapshot(self):
        self._snapshot_due.set()

    def _run_snapshots(self):
        while not self._stop.is_set():
            self._snapshot_due.wait()
            if self._stop.is_set():
                return
            self._stop.wait(SNAPSHOT_DEBOUNCE)
            self._snapshot_due.clear()
            if self._connected.is_set():
                try:
                    self.push_snapshot()
                except Exception as error:
                    self._on_status("snapshot error: %s" % error)

    def _run_connection(self):
        attempt = 0
        while not self._stop.is_set():
            try:
                self._connect_and_serve()
                attempt = 0
            except Exception as error:
                if self._stop.is_set():
                    return
                self._on_status("error: %s" % error)
                if "401" in str(error) or "403" in str(error):
                    self._settings.forget_registration()
            self._connected.clear()
            self._on_status("disconnected")
            delay = self._backoff[min(attempt, len(self._backoff) - 1)]
            attempt += 1
            self._stop.wait(delay)

    def _connect_and_serve(self):
        url = websocket_url(self._settings.backend_url(), self._settings.token())
        client = self._client_factory(url)
        client.connect()
        self._client = client
        self._connected.set()
        self._on_status("connected")
        client.send_text(frames.encode_frame(self._hello_builder()))
        while not self._stop.is_set():
            self._dispatch(frames.decode_frame(client.receive_text()))

    def _dispatch(self, frame):
        kind = frame["type"]
        if kind == constants.HELLO_ACK:
            self._reconcile(frame)
            self.push_snapshot()
        elif kind == constants.TOOL_CALL:
            if self._authorized is not None:
                self._authorized.register(frame)
            self._work.put(frame)
        elif kind == constants.MCP_REQUEST:
            self._work.put(frame)
        elif kind == constants.CHAT_EVENT:
            self._on_chat_event(frame)
        elif kind == constants.CANCEL_RUN:
            self._executor.cancel_run(frame.get("run_id"))

    def _reconcile(self, ack):
        backend_pending = set(ack.get("pending_calls") or [])
        for call_id in backend_pending:
            stored = self._ledger.result_frame(call_id)
            if stored is not None:
                self.send(stored)
        self.send(frames.pending_calls_frame(self._ledger.running_ids()))

    def _run_worker(self):
        while not self._stop.is_set():
            frame = self._work.get()
            if frame is None:
                return
            try:
                if frame["type"] == constants.TOOL_CALL:
                    self._serve_tool_call(frame)
                else:
                    self._serve_mcp(frame)
            except Exception as error:
                self._on_status("worker error: %s" % error)

    def _serve_tool_call(self, frame):
        def report(stage, fraction):
            progress = frames.progress_frame(frame["call_id"], stage, fraction)
            self._on_progress(progress)
            self.send(progress)

        result = self._executor.execute_call(frame, report)
        self._on_tool_result(result, frame.get("tool"))
        if self.send(result):
            self._ledger.mark_delivered(frame["call_id"])
        self.push_snapshot()

    def _serve_mcp(self, frame):
        envelope = mcp_envelope(frame)
        response = self._dispatcher.handle(envelope) if envelope is not None else None
        if response is not None:
            self.send(frames.mcp_response_frame(frame["id"], response))
