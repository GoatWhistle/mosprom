import io
import json
import unittest
from urllib import error

from Brim.protocol.backend_http import BackendHttpClient, BackendHttpError, encode_multipart
from Brim.settings import MemoryStore, PluginSettings, RegisteredConnection


class Response(object):
    def __init__(self, body=b"{}", headers=None):
        self._body = body
        self.headers = headers or {}

    def read(self):
        return self._body


class Opener(object):
    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []

    def __call__(self, req, timeout=None):
        self.requests.append(req)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class HttpTests(unittest.TestCase):
    def client(self, *replies):
        settings = PluginSettings(MemoryStore({"token": "T", "backend_url": "http://b:1/"}))
        opener = Opener(*replies)
        return BackendHttpClient(settings, opener), opener

    def test_authorized_json_request(self):
        client, opener = self.client(Response(b'{"id": "c1"}'))
        self.assertEqual(client.send_message("c1", "hi", ["a"], "ask"), {"id": "c1"})
        req = opener.requests[0]
        self.assertEqual(req.full_url, "http://b:1/api/v1/conversations/c1/messages")
        self.assertEqual(req.get_header("Authorization"), "Bearer T")
        self.assertEqual(json.loads(req.data.decode()), {"text": "hi", "attachment_ids": ["a"], "mode": "ask"})

    def test_register_is_not_authorized(self):
        client, opener = self.client(Response(b'{"token": "x"}'))
        client.register("inst")
        self.assertIsNone(opener.requests[0].get_header("Authorization"))

    def test_http_error_carries_status(self):
        failure = error.HTTPError("u", 409, "x", {}, io.BytesIO(b'{"code": "run_active"}'))
        client, _ = self.client(failure)
        with self.assertRaises(BackendHttpError) as caught:
            client.stop_run("r")
        self.assertEqual(caught.exception.status, 409)
        self.assertIn("run_active", str(caught.exception))

    def test_unreachable(self):
        client, _ = self.client(error.URLError("down"))
        with self.assertRaises(BackendHttpError):
            client.health()

    def test_multipart_contains_fields_and_file(self):
        content_type, body = encode_multipart([("kind", "gcode")], "file", "a.part0", b"\x00\x01")
        self.assertIn("boundary=", content_type)
        self.assertIn(b'name="kind"', body)
        self.assertIn(b'filename="a.part0"', body)
        self.assertIn(b"\x00\x01", body)

    def test_chunk_upload_fields(self):
        client, opener = self.client(Response(b'{"complete": false}'))
        client.upload_artifact_chunk("r1", "3mf", 4, 1, 3, "abc", b"data")
        body = opener.requests[0].data
        for needle in (b'name="scene_version"', b"\r\n4\r\n", b'name="chunk_index"', b'name="chunk_count"', b'name="sha256"'):
            self.assertIn(needle, body)


class SettingsTests(unittest.TestCase):
    def test_backend_url_validation_and_token_reset(self):
        settings = PluginSettings(MemoryStore({"token": "T"}))
        self.assertEqual(settings.backend_url(), "http://localhost:8000")
        with self.assertRaises(ValueError):
            settings.set_backend_url("localhost:9000")
        settings.set_backend_url("http://10.0.0.5:8000/")
        self.assertEqual(settings.backend_url(), "http://10.0.0.5:8000")
        self.assertEqual(settings.token(), "")

    def test_instance_id_is_stable(self):
        settings = PluginSettings(MemoryStore())
        self.assertEqual(settings.instance_id(), settings.instance_id())

    def test_llm_key_is_kept_when_field_is_empty(self):
        settings = PluginSettings(MemoryStore())
        settings.set_llm("https://x/v1", "m", "secret")
        settings.set_llm("https://x/v1", "m2", "")
        self.assertEqual(settings.llm(), {"base_url": "https://x/v1", "model": "m2", "api_key": "secret"})
        self.assertTrue(settings.llm_configured())

    def test_registration_retries_with_new_id_on_conflict(self):
        settings = PluginSettings(MemoryStore({"instance_id": "taken"}))

        class Http(object):
            def __init__(self):
                self.ids = []

            def register(self, instance_id):
                self.ids.append(instance_id)
                if instance_id == "taken":
                    raise BackendHttpError("conflict", 409)
                return {"token": "NEW"}

        http = Http()
        self.assertEqual(settings.ensure_registered(http), "NEW")
        self.assertEqual(len(http.ids), 2)
        self.assertNotEqual(http.ids[1], "taken")

    def test_concurrent_registration_happens_once(self):
        import threading
        import time

        settings = PluginSettings(MemoryStore())

        class Http(object):
            def __init__(self):
                self.calls = 0

            def register(self, instance_id):
                self.calls += 1
                time.sleep(0.05)
                return {"token": "ONE"}

        http = Http()
        threads = [threading.Thread(target=settings.ensure_registered, args=(http,)) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(http.calls, 1)
        self.assertEqual(settings.token(), "ONE")

    def test_registered_connection_registers_lazily(self):
        settings = PluginSettings(MemoryStore())
        connection = RegisteredConnection(settings)

        class Http(object):
            def register(self, instance_id):
                return {"token": "Z"}

        connection.bind(Http())
        self.assertEqual(connection.token(), "Z")
        connection.forget_registration()
        self.assertEqual(settings.token(), "")

    def test_language_and_theme_defaults(self):
        settings = PluginSettings(MemoryStore())
        self.assertEqual((settings.language(), settings.theme()), ("ru", "dark"))
        settings.set_language("en")
        settings.set_theme("light")
        self.assertEqual((settings.language(), settings.theme()), ("en", "light"))


if __name__ == "__main__":
    unittest.main()
