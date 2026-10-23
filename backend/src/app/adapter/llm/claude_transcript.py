import base64
import json
import uuid

from app.domain.chat import ChatMessage, ChatRequest, Role, ToolCall, ToolDefinition
from app.domain.errors import ModelMalformedResponse
from app.domain.jsonvalue import JsonObject

TOOL_PROTOCOL = (
    "The conversation so far is given as a transcript of <user>, <assistant> and <tool_result> "
    "blocks. Write the next assistant turn. You have no native tools in this session: never try "
    "to invoke a tool directly, it will fail. The tools listed below are executed by the client "
    "after your answer. To call them, put them into the tool_calls field of your structured "
    "answer with their arguments as a JSON object matching the tool's parameters schema; their "
    "results will arrive in a later turn as <tool_result> blocks. Leave tool_calls empty only to "
    "reply to the user with text. Available tools:"
)


def system_prompt(request: ChatRequest) -> str:
    parts = [item.text for item in request.messages if item.role is Role.SYSTEM and item.text]
    if request.tools:
        parts.append("\n".join([TOOL_PROTOCOL, *(_tool(item) for item in request.tools)]))
    return "\n\n".join(parts)


def content_blocks(request: ChatRequest) -> list[JsonObject]:
    blocks: list[JsonObject] = []
    for message in request.messages:
        if message.role is Role.SYSTEM:
            continue
        blocks.append({"type": "text", "text": _render(message)})
        for image in message.images:
            blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": image.mime_type,
                        "data": base64.b64encode(image.data).decode("ascii"),
                    },
                }
            )
    return blocks


def output_schema(tools: tuple[ToolDefinition, ...]) -> JsonObject:
    call: JsonObject = {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "arguments"],
        "properties": {
            "name": {"type": "string", "enum": [item.name for item in tools]},
            "arguments": {"type": "object"},
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["text", "tool_calls"],
        "properties": {
            "text": {"type": "string"},
            "tool_calls": {"type": "array", "items": call},
        },
    }


def parse_output(
    output: object, tools: tuple[ToolDefinition, ...]
) -> tuple[str, tuple[ToolCall, ...]]:
    if not isinstance(output, dict):
        raise ModelMalformedResponse("Claude returned no structured output")
    text, raw_calls = output.get("text", ""), output.get("tool_calls") or []
    if not isinstance(text, str) or not isinstance(raw_calls, list):
        raise ModelMalformedResponse("Claude structured output has the wrong shape")
    names = {item.name for item in tools}
    calls = []
    for item in raw_calls:
        if not isinstance(item, dict):
            raise ModelMalformedResponse("Claude tool call must be an object")
        name, arguments = item.get("name"), item.get("arguments")
        if name not in names or not isinstance(name, str) or not isinstance(arguments, dict):
            raise ModelMalformedResponse("Claude called an unknown tool or sent bad arguments")
        calls.append(ToolCall(id=f"call_{uuid.uuid4().hex}", name=name, arguments=arguments))
    return text, tuple(calls)


def _tool(tool: ToolDefinition) -> str:
    return json.dumps(
        {"name": tool.name, "description": tool.description, "parameters": tool.parameters},
        ensure_ascii=False,
    )


def _render(message: ChatMessage) -> str:
    if message.role is Role.TOOL:
        return f'<tool_result id="{message.tool_call_id or ""}">\n{message.text}\n</tool_result>'
    lines = [f"<{message.role.value}>"]
    if message.text:
        lines.append(message.text)
    for call in message.tool_calls:
        arguments = json.dumps(call.arguments, ensure_ascii=False)
        lines.append(f'<tool_call id="{call.id}" name="{call.name}">{arguments}</tool_call>')
    lines.append(f"</{message.role.value}>")
    return "\n".join(lines)
