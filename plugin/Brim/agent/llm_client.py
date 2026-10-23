import json
import socket
import uuid
from urllib import error, request

DEFAULT_TIMEOUT = 300.0
MAX_ERROR_TEXT = 300


class LlmError(Exception):
    pass


def _endpoint(base_url, path):
    return base_url.rstrip("/") + path


def _error_text(failure):
    try:
        body = failure.read().decode("utf-8", "replace")
    except Exception:
        body = ""
    try:
        detail = json.loads(body)
        if isinstance(detail, dict):
            message = detail.get("error") or detail.get("message") or detail
            if isinstance(message, dict):
                message = message.get("message") or message
            body = str(message)
    except ValueError:
        pass
    return body[:MAX_ERROR_TEXT]


def _arguments(raw):
    if isinstance(raw, dict):
        return raw, None
    try:
        value = json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}, "arguments are not valid JSON"
    if not isinstance(value, dict):
        return {}, "arguments must be a JSON object"
    return value, None


def parse_completion(payload):
    try:
        message = payload["choices"][0]["message"]
    except (KeyError, IndexError, TypeError):
        raise LlmError("the model response has no choices[0].message")
    content = message.get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    calls = []
    for item in message.get("tool_calls") or []:
        function = item.get("function") or {}
        name = function.get("name")
        if not isinstance(name, str) or not name:
            raise LlmError("the model returned a tool call without a name")
        arguments, problem = _arguments(function.get("arguments"))
        calls.append({"id": item.get("id") or "call_" + uuid.uuid4().hex, "name": name,
                      "arguments": arguments, "raw_arguments": function.get("arguments"), "problem": problem})
    return {"text": content or "", "tool_calls": calls,
            "finish_reason": (payload["choices"][0] or {}).get("finish_reason")}


class LlmClient(object):
    def __init__(self, config, timeout=DEFAULT_TIMEOUT, opener=None):
        self._config = config
        self._timeout = timeout
        self._open = opener or request.urlopen

    def _request(self, method, path, body=None):
        config = self._config()
        if not config.get("base_url") or not config.get("model"):
            raise LlmError("LLM URL and model are not configured")
        headers = {"Accept": "application/json"}
        if config.get("api_key"):
            headers["Authorization"] = "Bearer " + config["api_key"]
        data = None
        if body is not None:
            body = dict(body, model=config["model"])
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        prepared = request.Request(_endpoint(config["base_url"], path), data=data, headers=headers, method=method)
        try:
            with self._open(prepared, timeout=self._timeout) as response:
                raw = response.read()
        except error.HTTPError as failure:
            raise LlmError("LLM returned HTTP %d: %s" % (failure.code, _error_text(failure)))
        except (error.URLError, socket.timeout, OSError) as failure:
            raise LlmError("LLM is unreachable: %s" % getattr(failure, "reason", failure))
        try:
            return json.loads(raw.decode("utf-8"))
        except ValueError:
            raise LlmError("LLM returned a response that is not JSON")

    def chat(self, messages, tools):
        body = {"messages": messages}
        if tools:
            body["tools"] = [{"type": "function", "function": {
                "name": tool["name"], "description": tool.get("description", ""),
                "parameters": tool.get("parameters") or {"type": "object", "properties": {}}}} for tool in tools]
        return parse_completion(self._request("POST", "/chat/completions", body))

    def models(self):
        payload = self._request("GET", "/models")
        items = payload.get("data") if isinstance(payload, dict) else None
        return [item.get("id") for item in items or [] if isinstance(item, dict)]
