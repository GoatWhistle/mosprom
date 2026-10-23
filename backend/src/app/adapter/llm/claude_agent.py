import asyncio
import tempfile
from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKError, ResultMessage, query

from app.adapter.llm.claude_transcript import (
    content_blocks,
    output_schema,
    parse_output,
    system_prompt,
)
from app.domain.chat import ChatRequest, ChatResponse, LlmConnection
from app.domain.errors import ModelFailure, ModelMalformedResponse, ModelTimeout


class ClaudeAgentChatAdapter:
    def __init__(self, timeout_s: float) -> None:
        self._timeout_s = timeout_s

    async def chat(self, connection: LlmConnection, request: ChatRequest) -> ChatResponse:
        try:
            async with asyncio.timeout(self._timeout_s):
                result = await self._run(connection, request)
        except TimeoutError as exc:
            raise ModelTimeout() from exc
        except ClaudeSDKError as exc:
            raise ModelFailure(f"Claude Agent SDK failed: {type(exc).__name__}") from exc
        if result is None:
            raise ModelFailure("Claude Agent SDK returned no result")
        if result.is_error:
            raise ModelFailure(
                f"Claude Agent SDK returned {result.subtype} (HTTP {result.api_error_status})"
            )
        if request.tools:
            text, calls = parse_output(result.structured_output, request.tools)
        else:
            text, calls = result.result or "", ()
        if not text and not calls:
            raise ModelMalformedResponse("Claude returned neither text nor tool calls")
        return ChatResponse(text=text, tool_calls=calls, finish_reason=result.stop_reason)

    async def aclose(self) -> None:
        return None

    async def _run(self, connection: LlmConnection, request: ChatRequest) -> ResultMessage | None:
        result: ResultMessage | None = None
        with tempfile.TemporaryDirectory(prefix="brim-claude-") as cwd:
            options = _options(connection, request, cwd)
            async for message in query(prompt=_prompt(request), options=options):
                if isinstance(message, ResultMessage):
                    result = message
        return result


def _options(connection: LlmConnection, request: ChatRequest, cwd: str) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        model=connection.model,
        system_prompt=system_prompt(request),
        tools=[],
        setting_sources=[],
        cwd=cwd,
        env={"CLAUDE_CODE_OAUTH_TOKEN": connection.api_key, "ANTHROPIC_API_KEY": ""},
        output_format=(
            {"type": "json_schema", "schema": output_schema(request.tools)}
            if request.tools
            else None
        ),
    )


async def _prompt(request: ChatRequest) -> AsyncIterator[dict[str, Any]]:
    yield {
        "type": "user",
        "message": {"role": "user", "content": content_blocks(request)},
        "parent_tool_use_id": None,
        "session_id": "",
    }
