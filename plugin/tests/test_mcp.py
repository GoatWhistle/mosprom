import base64
import json
import unittest
from urllib import error, request

from tests.test_executor import build
from Brim.protocol.local_mcp import LocalMcpServer
from Brim.protocol.mcp import McpDispatcher
from Brim.protocol.tools import load_tools


def rpc(method, params=None, request_id=1):
    message = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        message["id"] = request_id
    if params is not None:
        message["params"] = params
    return message


def dispatcher_for(executor):
    return McpDispatcher(load_tools(), executor.execute)


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.executor, self.port, _ = build()
        self.dispatcher = dispatcher_for(self.executor)

    def test_initialize_and_list(self):
        init = self.dispatcher.handle(rpc("initialize", {}))
        self.assertIn("tools", init["result"]["capabilities"])
        tools = self.dispatcher.handle(rpc("tools/list"))["result"]["tools"]
        names = [tool["name"] for tool in tools]
        self.assertIn("apply_changes", names)
        self.assertNotIn("ask_user", names)
        annotations = dict((tool["name"], tool["annotations"]) for tool in tools)
        self.assertTrue(annotations["inspect_profile"]["readOnlyHint"])
        self.assertFalse(annotations["apply_changes"]["readOnlyHint"])

    def test_call_returns_text_content(self):
        reply = self.dispatcher.handle(rpc("tools/call", {"name": "inspect_profile", "arguments": {}}))
        payload = json.loads(reply["result"]["content"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertFalse(reply["result"]["isError"])

    def test_render_returns_image_block(self):
        reply = self.dispatcher.handle(rpc("tools/call", {"name": "render_scene", "arguments": {"view": "iso"}}))
        image = reply["result"]["content"][1]
        self.assertEqual(image["type"], "image")
        self.assertEqual(base64.b64decode(image["data"]), b"\x89PNG-fake")

    def test_mutations_run_without_backend_authorization(self):
        reply = self.dispatcher.handle(rpc("tools/call", {"name": "apply_changes",
                                                          "arguments": {"operations": [{"kind": "arrange"}]}}))
        self.assertFalse(reply["result"]["isError"])
        self.assertEqual(len(self.port.applied), 1)

    def test_errors(self):
        self.assertEqual(self.dispatcher.handle(rpc("nope"))["error"]["code"], -32601)
        self.assertEqual(self.dispatcher.handle(rpc("tools/call", {"name": "x"}))["error"]["code"], -32602)
        self.assertIsNone(self.dispatcher.handle(rpc("notifications/initialized", request_id=None)))
        self.assertEqual(self.dispatcher.handle_text("{")["error"]["code"], -32700)
        self.assertEqual(self.dispatcher.handle({"id": 1})["error"]["code"], -32600)

    def test_batch(self):
        replies = self.dispatcher.handle_text(json.dumps([rpc("ping", request_id=1), rpc("ping", request_id=None)]))
        self.assertEqual(len(replies), 1)


class LocalServerTests(unittest.TestCase):
    def setUp(self):
        executor, self.port, _ = build()
        self.server = LocalMcpServer(dispatcher_for(executor))
        self.url = "http://127.0.0.1:%d/mcp" % self.server.start()
        self.addCleanup(self.server.stop)

    def post(self, body, token="good", headers=None, url=None):
        data = json.dumps(body).encode("utf-8")
        head = {"Content-Type": "application/json"}
        if token is not None:
            head["Authorization"] = "Bearer " + (self.server.token() if token == "good" else token)
        head.update(headers or {})
        try:
            with request.urlopen(request.Request(url or self.url, data=data, headers=head, method="POST"), timeout=5) as response:
                return response.status, response.read()
        except error.HTTPError as failure:
            return failure.code, failure.read()

    def test_requires_token(self):
        self.assertEqual(self.post(rpc("ping"), token=None)[0], 401)
        self.assertEqual(self.post(rpc("ping"), token="wrong")[0], 401)

    def test_rejects_browser_origin_and_foreign_host(self):
        self.assertEqual(self.post(rpc("ping"), headers={"Origin": "http://evil.example"})[0], 401)
        self.assertEqual(self.post(rpc("ping"), headers={"Host": "evil.example"})[0], 401)

    def test_listens_on_loopback_only(self):
        self.assertEqual(self.server._server.server_address[0], "127.0.0.1")

    def test_ping_and_list(self):
        status, body = self.post(rpc("tools/list"))
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body.decode("utf-8"))["result"]["tools"])

    def test_notification_gets_202(self):
        self.assertEqual(self.post(rpc("notifications/initialized", request_id=None))[0], 202)

    def test_slice_runs_over_http(self):
        status, body = self.post(rpc("tools/call", {"name": "slice", "arguments": {}}))
        payload = json.loads(json.loads(body.decode("utf-8"))["result"]["content"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertEqual(self.port.slices, 1)

    def test_unknown_path(self):
        self.assertEqual(self.post(rpc("ping"), url=self.url.replace("/mcp", "/other"))[0], 404)


if __name__ == "__main__":
    unittest.main()
