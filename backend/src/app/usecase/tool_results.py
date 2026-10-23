import json

from app.domain.jsonvalue import JsonObject
from app.domain.protocol import OUTCOME_UNKNOWN
from app.usecase.dto.run import TranscriptEntry
from app.usecase.dto.tools import CallStatus, ToolCallDTO


def call_ok(call: ToolCallDTO) -> bool:
    return call.status is CallStatus.COMPLETED


def error_code(call: ToolCallDTO) -> str | None:
    if call.status is CallStatus.OUTCOME_UNKNOWN:
        return OUTCOME_UNKNOWN
    if call.error is not None and isinstance(call.error.get("code"), str):
        return str(call.error["code"])
    return None


def result_entry(call: ToolCallDTO) -> TranscriptEntry:
    body: JsonObject = {
        "ok": call_ok(call),
        "result": call.result or {},
        "error": call.error,
        "applied": list(call.applied),
        "scene_version": call.scene_version,
    }
    if call.status is CallStatus.OUTCOME_UNKNOWN:
        body["error"] = {
            "code": OUTCOME_UNKNOWN,
            "message": "The plugin did not confirm this call; inspect the scene before acting.",
        }
    attachment = (call.result or {}).get("attachment_id")
    return TranscriptEntry(
        role="tool",
        content=json.dumps(body, ensure_ascii=False),
        tool_call_id=call.llm_call_id,
        attachment_ids=(attachment,) if isinstance(attachment, str) else (),
    )


def error_entry(llm_call_id: str, code: str, message: str) -> TranscriptEntry:
    body = {"ok": False, "error": {"code": code, "message": message}}
    return TranscriptEntry(
        role="tool", content=json.dumps(body, ensure_ascii=False), tool_call_id=llm_call_id
    )
