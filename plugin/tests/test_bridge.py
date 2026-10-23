import time
import unittest

from tests.fakeserver import FakeSocketServer
from tests.test_executor import build
from Brim.protocol import frames
from Brim.protocol.authorization import AuthorizedCalls
from Brim.protocol.bridge import BridgeConnection, websocket_url
from Brim.protocol.mcp import McpDispatcher
from Brim.protocol.tools import load_tools
from Brim.protocol.websocket_client import WebSocketClient, WebSocketError


class Settings(object):
    def __init__(self, url):
        self.url = url
        self.forgotten = 0

    def backend_url(self):
        return self.url

    def token(self):
        return "tok en"

    def forget_registration(self):
        self.forgotten += 1


def wait_for(predicate, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return True
        time.sleep(0.02)
    return False


class UrlTests(unittest.TestCase):
    def test_websocket_url(self):
        self.assertEqual(websocket_url("http://h:8000/", "a b"), "ws://h:8000/api/v1/instances/ws?token=a%20b")
        self.assertEqual(websocket_url("https://h", "t"), "wss://h/api/v1/instances/ws?token=t")


class ClientTests(unittest.TestCase):
    def test_round_trip_and_large_frame(self):
        server = FakeSocketServer()
        self.addCleanup(server.close)
        client = WebSocketClient("ws://127.0.0.1:%d/x?token=1" % server.port)
        client.connect()
        self.addCleanup(client.close)
        big = "é" * 70000
        client.send_text('{"a": "%s"}' % big)
        self.assertEqual(server.get()["a"], big)
        wait_for(lambda: server.connections)
        server.send({"echo": big})
        self.assertEqual(__import__("json").loads(client.receive_text())["echo"], big)

    def test_rejected_handshake(self):
        server = FakeSocketServer(accept=False)
        self.addCleanup(server.close)
        with self.assertRaises(WebSocketError):
            WebSocketClient("ws://127.0.0.1:%d/x" % server.port).connect()


class BridgeTests(unittest.TestCase):
    def make(self, server, **extra):
        self.executor, self.port, self.http, self.ledger, _ = build()
        self.settings = Settings(server.url())
        self.statuses = []
        self.events = []
        self.results = []
        trusted = McpDispatcher(load_tools(), lambda n, a, r, m: self.executor.execute_mcp(n, a, r))
        self.authorized = AuthorizedCalls()
        bridge = BridgeConnection(
            self.settings, lambda: frames.hello_frame("inst", "7.10", ["classic"], {"name": "p"}), self.ledger,
            self.executor, trusted, lambda: (self.port.scene_version(), self.port.read_state()),
            on_chat_event=self.events.append, on_status=self.statuses.append,
            on_tool_result=lambda frame, tool: self.results.append((tool, frame["ok"])),
            authorized=self.authorized, backoff=(0.05,), **extra)
        self.addCleanup(bridge.stop)
        bridge.start()
        return bridge

    def next_of(self, server, kind):
        end = time.time() + 5
        while time.time() < end:
            frame = server.get(timeout=max(0.1, end - time.time()))
            if frame["type"] == kind:
                return frame
        self.fail("no %s frame" % kind)

    def test_hello_snapshot_tool_call_and_chat_event(self):
        server = FakeSocketServer()
        self.addCleanup(server.close)
        self.make(server)
        hello = self.next_of(server, "hello")
        self.assertEqual(hello["contract_version"], "2")
        self.assertIn("token=tok%20en", server.paths[0])
        wait_for(lambda: server.connections)
        server.send({"type": "hello_ack", "id": "a", "instance_id": "inst", "pending_calls": []})
        self.assertEqual(self.next_of(server, "state_snapshot")["scene_version"], 1)
        self.assertEqual(self.next_of(server, "pending_calls")["call_ids"], [])
        server.send({"type": "tool_call", "id": "t", "call_id": "c1", "run_id": "r1", "tool": "apply_changes",
                     "arguments": {"operations": [{"kind": "arrange"}]}, "expected_scene_version": 1})
        self.assertEqual(self.next_of(server, "state_snapshot")["scene_version"], 2)
        result = self.next_of(server, "tool_result")
        self.assertTrue(result["ok"])
        self.assertEqual(result["call_id"], "c1")
        self.assertEqual(self.results, [("apply_changes", True)])
        self.assertIsNotNone(self.authorized.match("c1", "apply_changes", {"operations": [{"kind": "arrange"}]}))
        server.send({"type": "chat_event", "id": "e", "event": "assistant_message", "payload": {"text": "hi"}})
        self.assertTrue(wait_for(lambda: self.events))

    def test_mcp_request_is_answered(self):
        server = FakeSocketServer()
        self.addCleanup(server.close)
        self.make(server)
        self.next_of(server, "hello")
        wait_for(lambda: server.connections)
        server.send({"type": "hello_ack", "id": "a", "pending_calls": []})
        server.send({"type": "mcp_request", "id": "m1", "jsonrpc": "2.0", "method": "tools/list", "request_id": 7})
        reply = self.next_of(server, "mcp_response")
        self.assertEqual(reply["request_id"], "m1")
        self.assertTrue(reply["jsonrpc"]["result"]["tools"])

    def test_reconnect_redelivers_stored_result_without_reapplying(self):
        server = FakeSocketServer()
        self.addCleanup(server.close)
        self.make(server)
        self.next_of(server, "hello")
        wait_for(lambda: server.connections)
        server.send({"type": "hello_ack", "id": "a", "pending_calls": []})
        call = {"type": "tool_call", "id": "t", "call_id": "c1", "run_id": "r1", "tool": "apply_changes",
                "arguments": {"operations": [{"kind": "arrange"}]}}
        server.send(call)
        self.next_of(server, "tool_result")
        server.drop()
        self.assertTrue(wait_for(lambda: len(server.connections) == 2))
        self.next_of(server, "hello")
        server.send({"type": "hello_ack", "id": "b", "pending_calls": ["c1"]}, index=1)
        again = self.next_of(server, "tool_result")
        self.assertEqual(again["call_id"], "c1")
        server.send(call, index=1)
        self.next_of(server, "tool_result")
        self.assertEqual(len(self.port.applied), 1)

    def test_cancel_run_frame(self):
        server = FakeSocketServer()
        self.addCleanup(server.close)
        self.make(server)
        self.next_of(server, "hello")
        wait_for(lambda: server.connections)
        server.send({"type": "cancel_run", "id": "c", "run_id": "r1"})
        self.assertTrue(wait_for(lambda: self.executor._is_cancelled("r1")))

    def test_auth_failure_forgets_registration_and_retries(self):
        server = FakeSocketServer(accept=False)
        self.addCleanup(server.close)
        self.make(server)
        self.assertTrue(wait_for(lambda: self.settings.forgotten >= 1 and len(server.paths) >= 2))

    def test_send_before_connection_reports_false(self):
        server = FakeSocketServer()
        self.addCleanup(server.close)
        bridge = self.make(server)
        bridge.stop()
        self.assertFalse(bridge.send({"type": "x", "id": "1"}))


if __name__ == "__main__":
    unittest.main()
