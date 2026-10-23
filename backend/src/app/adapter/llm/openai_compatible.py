import base64
import json

import httpx

from app.domain.chat import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    LlmConnection,
    Role,
    ToolCall,
    ToolDefinition,
)
from app.domain.errors import ModelFailure, ModelMalformedResponse, ModelTimeout
from app.domain.jsonvalue import JsonObject


class OpenAICompatibleChatAdapter:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse:
        url = connection.base_url.rstrip("/") + "/chat/completions"
        body: JsonObject = {
            "model": connection.model,
            "messages": [_message(item) for item in request.messages],
        }
        if request.tools:
            body["tools"] = [_tool(item) for item in request.tools]
        try:
            response = await self._client.post(
                url, json=body, headers={"Authorization": f"Bearer {connection.api_key}"}
            )
        except httpx.TimeoutException as exc:
            raise ModelTimeout() from exc
        except httpx.HTTPError as exc:
            raise ModelFailure(f"Language model request failed: {type(exc).__name__}") from exc
        if response.status_code >= 400:
            raise ModelFailure(f"Language model returned HTTP {response.status_code}")
        return _parse(response)

    async def aclose(self) -> None:
        await self._client.aclose()


def _message(message: ChatMessage) -> JsonObject:
    if message.role is Role.TOOL:
        return {"role": "tool", "tool_call_id": message.tool_call_id or "", "content": message.text}
    result: JsonObject = {"role": message.role.value}
    if message.images:
        parts: list[JsonObject] = [{"type": "text", "text": message.text}]
        for image in message.images:
            encoded = base64.b64encode(image.data).decode("ascii")
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{image.mime_type};base64,{encoded}"},
                }
            )
        result["content"] = list(parts)
    else:
        result["content"] = message.text
    if message.tool_calls:
        result["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.name, "arguments": json.dumps(call.arguments)},
            }
            for call in message.tool_calls
        ]
    return result


def _tool(tool: ToolDefinition) -> JsonObject:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
        },
    }


def _parse(response: httpx.Response) -> ChatResponse:
    try:
        payload = response.json()
        choice = payload["choices"][0]
        message = choice["message"]
        raw_calls = message.get("tool_calls") or []
        calls = tuple(_call(item) for item in raw_calls)
        content = message.get("content")
        text = content if isinstance(content, str) else ""
        reason = choice.get("finish_reason")
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ModelMalformedResponse() from exc
    if not text and not calls:
        raise ModelMalformedResponse("Language model returned neither text nor tool calls")
    return ChatResponse(
        text=text, tool_calls=calls, finish_reason=reason if isinstance(reason, str) else None
    )


def _call(item: object) -> ToolCall:
    if not isinstance(item, dict):
        raise TypeError("tool call must be an object")
    function = item["function"]
    arguments = json.loads(function.get("arguments") or "{}")
    if not isinstance(arguments, dict):
        raise TypeError("tool arguments must be an object")
    return ToolCall(id=str(item["id"]), name=str(function["name"]), arguments=arguments)
