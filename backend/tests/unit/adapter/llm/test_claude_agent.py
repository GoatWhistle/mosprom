import asyncio
from collections.abc import AsyncIterable, AsyncIterator
from typing import Any

import pytest
from claude_agent_sdk import ClaudeAgentOptions, CLIConnectionError, ResultMessage

from app.adapter.llm import claude_agent
from app.adapter.llm.claude_agent import ClaudeAgentChatAdapter
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

CONNECTION = LlmConnection(base_url="claude-agent", model="sonnet", api_key="sk-ant-oat-secret")
TOOLS = (
    ToolDefinition(name="slice", description="Slice the plate", parameters={"type": "object"}),
    ToolDefinition(name="ask_user", description="Ask", parameters={"type": "object"}),
)
REQUEST = ChatRequest(
    messages=(
        ChatMessage(role=Role.SYSTEM, text="You configure prints"),
        ChatMessage(role=Role.USER, text="look", images=(ImagePart("image/png", b"\x89PNG"),)),
        ChatMessage(
            role=Role.ASSISTANT, tool_calls=(ToolCall(id="c1", name="slice", arguments={}),)
        ),
        ChatMessage(role=Role.TOOL, text='{"ok": true}', tool_call_id="c1"),
    ),
    tools=TOOLS,
)


def result(**overrides: Any) -> ResultMessage:
    fields: dict[str, Any] = {
        "subtype": "success",
        "duration_ms": 120,
        "duration_api_ms": 100,
        "is_error": False,
        "num_turns": 1,
        "session_id": "session",
        "stop_reason": "end_turn",
        "structured_output": {"text": "", "tool_calls": []},
    }
    return ResultMessage(**(fields | overrides))


class FakeQuery:
    def __init__(self, messages: list[Any]) -> None:
        self.messages = messages
        self.options: list[ClaudeAgentOptions] = []
        self.prompts: list[dict[str, Any]] = []

    async def __call__(
        self, *, prompt: AsyncIterable[dict[str, Any]], options: ClaudeAgentOptions
    ) -> AsyncIterator[Any]:
        self.options.append(options)
        self.prompts.extend([item async for item in prompt])
        for message in self.messages:
            if isinstance(message, Exception):
                raise message
            yield message


def install(monkeypatch: pytest.MonkeyPatch, messages: list[Any]) -> FakeQuery:
    fake = FakeQuery(messages)
    monkeypatch.setattr(claude_agent, "query", fake)
    return fake


async def test_tool_calls_come_from_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    output = {
        "text": "Slicing",
        "tool_calls": [
            {"name": "slice", "arguments": {}},
            {"name": "ask_user", "arguments": {"questions": ["q"]}},
        ],
    }
    install(monkeypatch, [result(structured_output=output)])

    response = await ClaudeAgentChatAdapter(5).chat(CONNECTION, REQUEST)

    assert response.text == "Slicing"
    assert [call.name for call in response.tool_calls] == ["slice", "ask_user"]
    assert response.tool_calls[1].arguments == {"questions": ["q"]}
    assert len({call.id for call in response.tool_calls}) == 2
    assert response.finish_reason == "end_turn"


async def test_options_isolate_the_cli_and_pass_the_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = install(monkeypatch, [result(structured_output={"text": "hi", "tool_calls": []})])

    await ClaudeAgentChatAdapter(5).chat(CONNECTION, REQUEST)

    options = fake.options[0]
    assert options.model == "sonnet"
    assert options.tools == [] and options.setting_sources == []
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat-secret"
    assert options.env["ANTHROPIC_API_KEY"] == ""
    assert isinstance(options.system_prompt, str)
    assert options.system_prompt.startswith("You configure prints")
    assert '"name": "ask_user"' in options.system_prompt
    assert options.output_format is not None
    schema = options.output_format["schema"]
    assert schema["properties"]["tool_calls"]["items"]["properties"]["name"]["enum"] == [
        "slice",
        "ask_user",
    ]


async def test_transcript_keeps_images_and_tool_history(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [result(structured_output={"text": "hi", "tool_calls": []})])

    await ClaudeAgentChatAdapter(5).chat(CONNECTION, REQUEST)

    blocks = fake.prompts[0]["message"]["content"]
    assert [block["type"] for block in blocks] == ["text", "image", "text", "text"]
    assert blocks[0]["text"] == "<user>\nlook\n</user>"
    assert blocks[1]["source"]["media_type"] == "image/png"
    assert '<tool_call id="c1" name="slice">{}</tool_call>' in blocks[2]["text"]
    assert blocks[3]["text"].startswith('<tool_result id="c1">')


async def test_plain_text_without_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = install(monkeypatch, [result(structured_output=None, result="Summary")])
    request = ChatRequest(messages=REQUEST.messages)

    response = await ClaudeAgentChatAdapter(5).chat(CONNECTION, request)

    assert response.text == "Summary" and response.tool_calls == ()
    assert fake.options[0].output_format is None


@pytest.mark.parametrize(
    "output",
    [
        None,
        {"text": "", "tool_calls": []},
        {"text": 1, "tool_calls": []},
        {"text": "", "tool_calls": [{"name": "rm_rf", "arguments": {}}]},
        {"text": "", "tool_calls": [{"name": "slice", "arguments": "{}"}]},
    ],
    ids=["missing", "empty", "bad-text", "unknown-tool", "string-arguments"],
)
async def test_malformed_structured_output(monkeypatch: pytest.MonkeyPatch, output: object) -> None:
    install(monkeypatch, [result(structured_output=output)])

    with pytest.raises(ModelMalformedResponse):
        await ClaudeAgentChatAdapter(5).chat(CONNECTION, REQUEST)


@pytest.mark.parametrize(
    "messages",
    [
        [],
        [result(is_error=True, subtype="success", api_error_status=429)],
        [CLIConnectionError("cli missing sk-ant-oat-secret")],
    ],
    ids=["no-result", "error-result", "sdk-error"],
)
async def test_failures_become_model_failure(
    monkeypatch: pytest.MonkeyPatch, messages: list[Any]
) -> None:
    install(monkeypatch, messages)

    with pytest.raises(ModelFailure) as caught:
        await ClaudeAgentChatAdapter(5).chat(CONNECTION, REQUEST)
    assert "secret" not in str(caught.value)


async def test_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    async def slow(
        *, prompt: AsyncIterable[dict[str, Any]], options: ClaudeAgentOptions
    ) -> AsyncIterator[Any]:
        await asyncio.sleep(1)
        yield result()

    monkeypatch.setattr(claude_agent, "query", slow)

    with pytest.raises(ModelTimeout):
        await ClaudeAgentChatAdapter(0.01).chat(CONNECTION, REQUEST)
