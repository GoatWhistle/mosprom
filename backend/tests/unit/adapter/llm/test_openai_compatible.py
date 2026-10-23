import json

import httpx
import pytest

from app.adapter.llm.openai_compatible import OpenAICompatibleChatAdapter
from app.domain.chat import (
    ChatMessage,
    ChatRequest,
    ImagePart,
    LlmConnection,
    Role,
    ToolCall,
    ToolDefinition,
)
from app.domain.errors import ModelFailure, ModelMalformedResponse, ModelTimeout

CONNECTION = LlmConnection(base_url="http://llm/v1/", model="m", api_key="secret")
REQUEST = ChatRequest(
    messages=(
        ChatMessage(role=Role.SYSTEM, text="sys"),
        ChatMessage(role=Role.USER, text="look", images=(ImagePart("image/png", b"\x89PNG"),)),
        ChatMessage(
            role=Role.ASSISTANT, tool_calls=(ToolCall(id="c1", name="slice", arguments={}),)
        ),
        ChatMessage(role=Role.TOOL, text="{}", tool_call_id="c1"),
    ),
    tools=(ToolDefinition(name="slice", description="d", parameters={"type": "object"}),),
)


def adapter(handler: httpx.MockTransport) -> OpenAICompatibleChatAdapter:
    return OpenAICompatibleChatAdapter(httpx.AsyncClient(transport=handler))


async def test_request_shape_and_multiple_tool_calls() -> None:
    seen: dict[str, object] = {}

    def handle(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        message = {
            "content": None,
            "tool_calls": [
                {"id": "a", "type": "function", "function": {"name": "slice", "arguments": "{}"}},
                {
                    "id": "b",
                    "type": "function",
                    "function": {"name": "ask_user", "arguments": '{"questions": ["q"]}'},
                },
            ],
        }
        return httpx.Response(
            200, json={"choices": [{"message": message, "finish_reason": "tool_calls"}]}
        )

    result = await adapter(httpx.MockTransport(handle)).chat(CONNECTION, REQUEST)
    assert seen["url"] == "http://llm/v1/chat/completions"
    assert seen["auth"] == "Bearer secret"
    body = seen["body"]
    assert isinstance(body, dict)
    user = body["messages"][1]["content"]
    assert user[1]["image_url"]["url"].startswith("data:image/png;base64,")
    assert body["messages"][3] == {"role": "tool", "tool_call_id": "c1", "content": "{}"}
    assert body["tools"][0]["function"]["name"] == "slice"
    assert [call.name for call in result.tool_calls] == ["slice", "ask_user"]
    assert result.tool_calls[1].arguments == {"questions": ["q"]}


async def test_text_response() -> None:
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, json={"choices": [{"message": {"content": "hi"}}]})
    )
    result = await adapter(transport).chat(CONNECTION, REQUEST)
    assert result.text == "hi" and result.tool_calls == ()


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json"),
        httpx.Response(200, json={"choices": []}),
        httpx.Response(200, json={"choices": [{"message": {"content": ""}}]}),
        httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {"id": "a", "function": {"name": "x", "arguments": "{broken"}}
                            ],
                        }
                    }
                ]
            },
        ),
    ],
)
async def test_malformed_responses(response: httpx.Response) -> None:
    with pytest.raises(ModelMalformedResponse):
        await adapter(httpx.MockTransport(lambda _: response)).chat(CONNECTION, REQUEST)


async def test_http_error_does_not_leak_key() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(401, json={"error": "secret"}))
    with pytest.raises(ModelFailure) as caught:
        await adapter(transport).chat(CONNECTION, REQUEST)
    assert "secret" not in str(caught.value)


async def test_timeout_and_transport_errors() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    def refused(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down")

    with pytest.raises(ModelTimeout):
        await adapter(httpx.MockTransport(timeout)).chat(CONNECTION, REQUEST)
    with pytest.raises(ModelFailure):
        await adapter(httpx.MockTransport(refused)).chat(CONNECTION, REQUEST)
