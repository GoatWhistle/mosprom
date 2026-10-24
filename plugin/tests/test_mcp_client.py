import json
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from tests.agent_harness import Harness, calls_reply, done_reply
from tests.test_executor import build
from Brim.agent.hub import McpHub, model_name, tool_output
from Brim.agent.mcp_client import McpClientError, McpHttpClient, sse_messages
from Brim.protocol.local_mcp import LocalMcpServer
from Brim.protocol.mcp import McpDispatcher
from Brim.protocol.tools import load_tools


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class SseServer(object):
    def __init__(self, session="s-1", expire_once=False):
        self.requests = []
        self.headers = []
        self.expire_once = expire_once
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                return

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])).decode("utf-8"))
                owner.requests.append(body)
                owner.headers.append(dict(self.headers))
                if "id" in body and body["method"] != "initialize" and owner.expire_once and self.headers.get("Mcp-Session-Id"):
                    owner.expire_once = False
                    self.send_response(404)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                if "id" not in body:
                    self.send_response(202)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                result = owner.result(body)
                stream = ": keepalive\n\nevent: message\ndata: %s\n\n" % json.dumps(
                    {"jsonrpc": "2.0", "id": body["id"], "result": result})
                data = stream.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                if body["method"] == "initialize":
                    self.send_header("Mcp-Session-Id", session)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._server = _Server(("127.0.0.1", 0), Handler)
        self.url = "http://127.0.0.1:%d/mcp" % self._server.server_port
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def result(self, body):
        method = body["method"]
        if method == "initialize":
            return {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "sse"}}
        if method == "tools/list":
            if not (body.get("params") or {}).get("cursor"):
                return {"tools": [{"name": "echo", "inputSchema": {"type": "object"}}], "nextCursor": "2"}
            return {"tools": [{"name": "wipe", "annotations": {"destructiveHint": True}}]}
        if method == "tools/call":
            return {"content": [{"type": "text", "text": "echo:" + json.dumps(body["params"]["arguments"])}]}
        return {}

    def stop(self):
        self._server.shutdown()
        self._server.server_close()


def closed_port():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


class ClientTests(unittest.TestCase):
    def test_sse_parser_joins_data_lines_and_skips_comments(self):
        self.assertEqual(sse_messages(": c\ndata: {\"a\":\ndata: 1}\n\ndata: 2\n"), ['{"a":\n1}', "2"])

    def test_against_local_server_with_json_replies(self):
        executor, port, _ = build()
        server = LocalMcpServer(McpDispatcher(load_tools(), executor.execute))
        url = "http://127.0.0.1:%d/mcp" % server.start()
        self.addCleanup(server.stop)
        client = McpHttpClient(url, {"Authorization": "Bearer " + server.token()}, timeout=5)
        names = [tool["name"] for tool in client.list_tools()]
        self.assertIn("slice", names)
        result = client.call_tool("inspect_profile", {})
        self.assertTrue(json.loads(result["content"][0]["text"])["ok"])

    def test_wrong_token_is_a_clear_error(self):
        executor, _, _ = build()
        server = LocalMcpServer(McpDispatcher(load_tools(), executor.execute))
        url = "http://127.0.0.1:%d/mcp" % server.start()
        self.addCleanup(server.stop)
        with self.assertRaises(McpClientError) as caught:
            McpHttpClient(url, {"Authorization": "Bearer nope"}, timeout=5).list_tools()
        self.assertIn("401", str(caught.exception))

    def test_sse_server_session_pagination_and_headers(self):
        server = SseServer()
        self.addCleanup(server.stop)
        client = McpHttpClient(server.url, {"X-Key": "k"}, timeout=5)
        self.assertEqual([tool["name"] for tool in client.list_tools()], ["echo", "wipe"])
        self.assertEqual(client.call_tool("echo", {"a": 1})["content"][0]["text"], 'echo:{"a": 1}')
        methods = [item["method"] for item in server.requests]
        self.assertEqual(methods[:2], ["initialize", "notifications/initialized"])
        last = server.headers[-1]
        self.assertEqual(last.get("Mcp-Session-Id"), "s-1")
        self.assertEqual(last.get("MCP-Protocol-Version") or last.get("Mcp-Protocol-Version"), "2025-06-18")
        self.assertEqual(last.get("X-Key"), "k")
        self.assertIn("text/event-stream", last.get("Accept"))

    def test_expired_session_is_reinitialized_once(self):
        server = SseServer(expire_once=True)
        self.addCleanup(server.stop)
        client = McpHttpClient(server.url, timeout=5)
        client.list_tools()
        self.assertEqual([item["method"] for item in server.requests].count("initialize"), 2)

    def test_unreachable_server(self):
        with self.assertRaises(McpClientError):
            McpHttpClient("http://127.0.0.1:%d/mcp" % closed_port(), timeout=2).list_tools()


class HubTests(unittest.TestCase):
    def test_names_are_prefixed_and_sanitised(self):
        self.assertEqual(model_name("brim", "slice"), "slice")
        self.assertEqual(model_name("my.srv", "do it"), "my_srv__do_it")
        self.assertEqual(len(model_name("s", "x" * 100)), 64)

    def test_tool_output_collects_text_and_images(self):
        output = tool_output({"content": [{"type": "text", "text": "a"}, {"type": "image", "data": "aGk=",
                                                                           "mimeType": "image/png"}], "isError": True})
        self.assertEqual(output["text"], "a")
        self.assertEqual(output["images"][0]["data"], b"hi")
        self.assertTrue(output["is_error"])

    def test_external_tools_are_merged_and_routed(self):
        executor, _, _ = build()
        server = SseServer()
        self.addCleanup(server.stop)
        servers = [{"name": "ext", "url": server.url, "headers": {}, "enabled": True},
                   {"name": "off", "url": server.url, "headers": {}, "enabled": False}]
        hub = McpHub(McpDispatcher(load_tools(), executor.execute), lambda: servers,
                     lambda url, headers: McpHttpClient(url, headers, timeout=5))
        self.assertEqual(hub.refresh(), [])
        names = [tool["name"] for tool in hub.tools()]
        self.assertIn("slice", names)
        self.assertIn("ext__echo", names)
        self.assertEqual(hub.describe("ext__wipe")["annotations"], {"destructiveHint": True})
        self.assertEqual(hub.call("ext__echo", {"b": 2})["text"], 'echo:{"b": 2}')
        status = hub.status()
        self.assertEqual(status["ext"]["tools"], 2)
        self.assertEqual(status["off"]["state"], "off")

    def test_unavailable_server_is_skipped_with_a_warning(self):
        executor, _, _ = build()
        servers = [{"name": "down", "url": "http://127.0.0.1:%d/mcp" % closed_port(), "headers": {}, "enabled": True}]
        hub = McpHub(McpDispatcher(load_tools(), executor.execute), lambda: servers,
                     lambda url, headers: McpHttpClient(url, headers, timeout=2))
        warnings = hub.refresh()
        self.assertEqual(warnings[0][0], "down")
        self.assertEqual(hub.status()["down"]["state"], "error")
        self.assertIn("slice", [tool["name"] for tool in hub.tools()])


class LoopWithExternalServersTests(unittest.TestCase):
    def test_failed_external_server_does_not_break_the_turn(self):
        servers = [{"name": "down", "url": "http://127.0.0.1:%d/mcp" % closed_port(), "headers": {}, "enabled": True}]
        harness = Harness([calls_reply(("p1", "inspect_profile", {})), done_reply()], servers=servers)
        self.addCleanup(harness.stop)
        harness.run(text="hi")
        self.assertIn("warning", harness.kinds())
        self.assertEqual(harness.tool_messages()[0]["brim_status"], "ok")
        self.assertEqual(harness.conversation.messages()[-1]["content"], "Готово")

    def test_external_tool_needs_confirmation_in_ask_mode_unless_read_only(self):
        server = SseServer()
        self.addCleanup(server.stop)
        servers = [{"name": "ext", "url": server.url, "headers": {}, "enabled": True}]
        harness = Harness([calls_reply(("e1", "ext__echo", {"x": 1})), done_reply()], servers=servers)
        self.addCleanup(harness.stop)
        harness.run(text="hi")
        card = [item for kind, item in harness.events if kind == "confirm"][0]
        self.assertEqual(card["server"], "ext")
        self.assertEqual(harness.tool_messages()[0]["content"], 'echo:{"x": 1}')

    def test_destructive_external_tool_is_confirmed_in_auto_mode(self):
        server = SseServer()
        self.addCleanup(server.stop)
        servers = [{"name": "ext", "url": server.url, "headers": {}, "enabled": True}]
        harness = Harness([calls_reply(("e1", "ext__echo", {}), ("w1", "ext__wipe", {})), done_reply()],
                          servers=servers, mode="auto")
        self.addCleanup(harness.stop)
        harness.decisions.append(("reject", ""))
        harness.run(text="hi")
        cards = [item for kind, item in harness.events if kind == "confirm"]
        self.assertEqual([card["call_id"] for card in cards], ["w1"])
        self.assertEqual([item["brim_status"] for item in harness.tool_messages()], ["ok", "rejected"])


if __name__ == "__main__":
    unittest.main()
