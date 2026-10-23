import json
import uuid
from urllib import error as urlerror
from urllib import request as urlrequest

from . import constants


class BackendHttpError(Exception):
    def __init__(self, message, status=None):
        Exception.__init__(self, message)
        self.status = status


def encode_multipart(fields, file_field, file_name, file_bytes):
    boundary = "brim" + uuid.uuid4().hex
    lines = []
    for name, value in fields:
        lines.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n" % (boundary, name, value)).encode("utf-8"))
    lines.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                  "Content-Type: application/octet-stream\r\n\r\n" % (boundary, file_field, file_name)).encode("utf-8"))
    lines.append(file_bytes)
    lines.append(("\r\n--%s--\r\n" % boundary).encode("utf-8"))
    return "multipart/form-data; boundary=%s" % boundary, b"".join(lines)


class BackendHttpClient(object):
    def __init__(self, settings, opener=None, timeout=60.0):
        self._settings = settings
        self._opener = opener or urlrequest.urlopen
        self._timeout = timeout

    def _url(self, path):
        return self._settings.backend_url().rstrip("/") + constants.API_PREFIX + path

    def _send(self, method, path, body=None, content_type=None, authorized=True, raw=False):
        headers = {}
        if authorized:
            headers["Authorization"] = "Bearer " + self._settings.token()
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            headers["Content-Type"] = content_type or "application/json"
        req = urlrequest.Request(self._url(path), data=data, headers=headers, method=method)
        try:
            response = self._opener(req, timeout=self._timeout)
            payload = response.read()
            response_headers = response.headers if hasattr(response, "headers") else {}
        except urlerror.HTTPError as http_error:
            detail = http_error.read().decode("utf-8", "replace")[:300]
            raise BackendHttpError("HTTP %s: %s" % (http_error.code, detail), http_error.code)
        except (urlerror.URLError, OSError) as network_error:
            raise BackendHttpError("backend unreachable: %s" % network_error)
        if raw:
            return payload, response_headers
        return json.loads(payload.decode("utf-8")) if payload else {}

    def register(self, instance_id):
        return self._send("POST", "/instances/register", {"instance_id": instance_id}, authorized=False)

    def put_llm(self, base_url, model, api_key):
        return self._send("PUT", "/instances/llm", {"base_url": base_url, "model": model, "api_key": api_key})

    def list_conversations(self):
        return self._send("GET", "/conversations")

    def create_conversation(self):
        return self._send("POST", "/conversations", {})

    def create_conversation_with(self, mode):
        return self._send("POST", "/conversations", {"mode": mode})

    def get_conversation(self, conversation_id):
        return self._send("GET", "/conversations/%s" % conversation_id)

    def send_message(self, conversation_id, text, attachment_ids, mode, client_message_id=None):
        body = {"text": text, "attachment_ids": list(attachment_ids), "mode": mode}
        if client_message_id:
            body["client_message_id"] = client_message_id
        return self._send("POST", "/conversations/%s/messages" % conversation_id, body)

    def put_project(self, conversation_id, state, sha256, active=True):
        body = {"state": state, "active": active}
        if sha256:
            body["sha256"] = sha256
        return self._send("PUT", "/conversations/%s/project" % conversation_id, body)

    def activate_conversation(self, conversation_id):
        return self._send("PUT", "/conversations/%s/active" % conversation_id)

    def set_mode(self, conversation_id, mode):
        return self._send("PUT", "/conversations/%s/mode" % conversation_id, {"mode": mode})

    def confirm(self, run_id, decision, text=None):
        body = {"decision": decision}
        if text:
            body["text"] = text
        return self._send("POST", "/runs/%s/confirmation" % run_id, body)

    def stop_run(self, run_id):
        return self._send("POST", "/runs/%s/stop" % run_id, {})

    def upload_attachment(self, file_name, file_bytes):
        content_type, body = encode_multipart([], "file", file_name, file_bytes)
        return self._send("POST", "/attachments", body, content_type)

    def download_attachment(self, attachment_id):
        return self._send("GET", "/attachments/%s" % attachment_id, raw=True)

    def upload_artifact_chunk(self, run_id, kind, scene_version, index, count, sha256, chunk, scene_epoch=""):
        fields = [("kind", kind), ("scene_epoch", scene_epoch), ("scene_version", scene_version), ("chunk_index", index),
                  ("chunk_count", count), ("sha256", sha256)]
        content_type, body = encode_multipart(fields, "file", "%s.part%d" % (kind, index), chunk)
        return self._send("POST", "/runs/%s/artifacts" % run_id, body, content_type)

    def list_artifacts(self, run_id):
        return self._send("GET", "/runs/%s/artifacts" % run_id)

    def get_run(self, run_id):
        return self._send("GET", "/runs/%s" % run_id)

    def health(self):
        return self._send("GET", "/health", authorized=False)

    def download_artifact(self, run_id, kind):
        return self._send("GET", "/runs/%s/artifacts/%s" % (run_id, kind), raw=True)
