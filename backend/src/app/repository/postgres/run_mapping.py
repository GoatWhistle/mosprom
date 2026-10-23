from datetime import datetime

from app.domain.jsonvalue import JsonObject
from app.domain.run import RunState
from app.usecase.dto.run import RunDTO, TranscriptEntry


def _params(run: RunDTO) -> dict[str, object]:
    return {
        "id": run.id,
        "conversation_id": run.conversation_id,
        "instance_id": run.instance_id,
        "state": run.state.value,
        "requirements_ready": run.requirements_ready,
        "requirements_summary": run.requirements_summary,
        "correction_key": run.correction_key,
        "correction_failures": run.correction_failures,
        "help_required": run.help_required,
        "steps": run.steps,
        "last_error": run.last_error,
        "created_at": run.created_at,
        "updated_at": run.updated_at,
        "finished_at": run.finished_at,
    }


def _run(row: tuple[object, ...]) -> RunDTO:
    assert isinstance(row[11], datetime) and isinstance(row[12], datetime)
    return RunDTO(
        id=str(row[0]),
        conversation_id=str(row[1]),
        instance_id=str(row[2]),
        state=RunState(str(row[3])),
        requirements_ready=bool(row[4]),
        requirements_summary=str(row[5]) if row[5] is not None else None,
        correction_key=str(row[6]) if row[6] is not None else None,
        correction_failures=int(str(row[7])),
        help_required=bool(row[8]),
        steps=int(str(row[9])),
        last_error=str(row[10]) if row[10] is not None else None,
        created_at=row[11],
        updated_at=row[12],
        finished_at=row[13] if isinstance(row[13], datetime) else None,
    )


def _entry_json(entry: TranscriptEntry) -> JsonObject:
    return {
        "role": entry.role,
        "content": entry.content,
        "tool_calls": list(entry.tool_calls),
        "tool_call_id": entry.tool_call_id,
        "attachment_ids": list(entry.attachment_ids),
        "extra": entry.extra,
    }


def _entry(raw: object) -> TranscriptEntry:
    assert isinstance(raw, dict)
    calls = raw.get("tool_calls")
    attachments = raw.get("attachment_ids")
    extra = raw.get("extra")
    tool_call_id = raw.get("tool_call_id")
    return TranscriptEntry(
        role=str(raw["role"]),
        content=str(raw.get("content") or ""),
        tool_calls=tuple(item for item in calls if isinstance(item, dict))
        if isinstance(calls, list)
        else (),
        tool_call_id=str(tool_call_id) if tool_call_id is not None else None,
        attachment_ids=tuple(str(item) for item in attachments)
        if isinstance(attachments, list)
        else (),
        extra=extra if isinstance(extra, dict) else {},
    )
