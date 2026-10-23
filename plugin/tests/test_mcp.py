import json
import unittest
from urllib import error, request

from tests.test_executor import build, call
from Brim.protocol.authorization import AuthorizedCalls, McpAuthorizationGate
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


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.executor, self.port, _, _, _ = build()
        self.dispatcher = McpDispatcher(load_tools(), lambda name, arguments, request_id, meta:
                                        self.executor.execute_mcp(name, arguments, request_id))

    def test_initialize_and_list(self):
        init = self.dispatcher.handle(rpc("initialize", {}))
        self.assertIn("tools", init["result"]["capabilities"])
        names = [tool["name"] for tool in self.dispatcher.handle(rpc("tools/list"))["result"]["tools"]]
        self.assertIn("apply_changes", names)

    def test_call_returns_text_content(self):
        reply = self.dispatcher.handle(rpc("tools/call", {"name": "inspect_profile", "arguments": {}}))
        payload = json.loads(reply["result"]["content"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertFalse(reply["result"]["isError"])

    def test_errors(self):
        self.assertEqual(self.dispatcher.handle(rpc("nope"))["error"]["code"], -32601)
        self.assertEqual(self.dispatcher.handle(rpc("tools/call", {"name": "x"}))["error"]["code"], -32602)
        self.assertIsNone(self.dispatcher.handle(rpc("notifications/initialized", request_id=None)))
        self.assertEqual(self.dispatcher.handle_text("{")["error"]["code"], -32700)
        self.assertEqual(self.dispatcher.handle({"id": 1})["error"]["code"], -32600)

    def test_batch(self):
        replies = self.dispatcher.handle_text(json.dumps([rpc("ping", request_id=1), rpc("ping", request_id=None)]))
        self.assertEqual(len(replies), 1)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.executor, self.port, _, _, _ = build()
        self.authorized = AuthorizedCalls()
        self.gate = McpAuthorizationGate(self.executor, self.authorized)
        self.ops = {"operations": [{"kind": "arrange"}]}

    def test_read_only_tools_pass(self):
        self.assertTrue(self.gate.handle("inspect_profile", {}, 1, {})["ok"])

    def test_mutation_without_backend_call_is_refused(self):
        outcome = self.gate.handle("apply_changes", self.ops, 1, {})
        self.assertEqual(outcome["error"]["code"], "execution_not_authorized")
        self.assertEqual(self.port.applied, [])

    def test_mutation_with_unknown_or_mismatching_call_is_refused(self):
        self.authorized.register(call("c1", "apply_changes", self.ops))
        for meta, arguments in (({"call_id": "zzz"}, self.ops), ({"call_id": "c1"}, {"operations": [{"kind": "delete", "object_ids": ["a"]}]})):
            self.assertEqual(self.gate.handle("apply_changes", arguments, 1, meta)["error"]["code"], "execution_not_authorized")
        self.assertEqual(self.gate.handle("slice", {}, 1, {"call_id": "c1"})["error"]["code"], "execution_not_authorized")
        self.assertEqual(self.port.applied, [])

    def test_mutation_matching_authorized_call_runs_once(self):
        frame = call("c1", "apply_changes", self.ops)
        self.authorized.register(frame)
        first = self.gate.handle("apply_changes", self.ops, 1, {"call_id": "c1"})
        second = self.gate.handle("apply_changes", self.ops, 2, {"call_id": "c1"})
        self.assertTrue(first["ok"])
        self.assertEqual(first, second)
        self.assertEqual(len(self.port.applied), 1)


class LocalServerTests(unittest.TestCase):
    def setUp(self):
        executor, self.port, _, _, _ = build()
        gate = McpAuthorizationGate(executor, AuthorizedCalls())
        self.server = LocalMcpServer(McpDispatcher(load_tools(), gate.handle))
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

    def test_mutation_is_refused_over_http(self):
        status, body = self.post(rpc("tools/call", {"name": "slice", "arguments": {}}))
        payload = json.loads(json.loads(body.decode("utf-8"))["result"]["content"][0]["text"])
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["error"]["code"], "execution_not_authorized")
        self.assertEqual(self.port.slices, 0)

    def test_unknown_path(self):
        self.assertEqual(self.post(rpc("ping"), url=self.url.replace("/mcp", "/other"))[0], 404)


if __name__ == "__main__":
    unittest.main()
