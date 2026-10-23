from app.domain.jsonvalue import JsonObject
from app.domain.run import RunState
from app.usecase.interface.storage import UnitOfWork


async def conversation_runtime(uow: UnitOfWork, conversation_id: str) -> JsonObject:
    run = await uow.runs.get_latest_for_conversation(conversation_id)
    if run is None:
        return {"run_id": None, "state": None, "pending": None, "result": None, "events": []}
    events = await uow.runs.list_events(run.id)
    pending: JsonObject | None = None
    if run.state is RunState.AWAITING_USER:
        question = await uow.runs.get_open_question_batch(run.id)
        if question is not None:
            pending = {
                "type": "question",
                "batch_id": question.id,
                "questions": list(question.questions),
            }
    elif run.state is RunState.AWAITING_CONFIRMATION:
        batch = await uow.batches.get_proposed_for_run(run.id)
        if batch is not None:
            pending = {
                "type": "confirmation",
                "batch_id": batch.id,
                "operations": list(batch.operations),
                "explanation": batch.explanation,
                "scene_epoch": batch.scene_epoch,
                "scene_version": batch.scene_version,
            }
    result: JsonObject | None = None
    if run.state is RunState.COMPLETED:
        calls = await uow.tool_calls.list_for_run(run.id)
        slices = [call for call in calls if call.tool == "slice" and call.result is not None]
        if slices:
            call = slices[-1]
            saved = await uow.artifacts.list_meta(run.id)
            artifacts: JsonObject = {
                item.kind: {"sha256": item.sha256, "size": item.size, "name": item.name}
                for item in saved
                if (item.scene_epoch, item.scene_version) == (call.scene_epoch, call.scene_version)
            }
            if {"gcode", "3mf"} <= artifacts.keys():
                result = {
                    "run_id": run.id,
                    "project_version": run.project_version,
                    "summary": (call.result or {}).get("slice") or {},
                    "artifacts": artifacts,
                }
    return {
        "run_id": run.id,
        "state": run.state.value,
        "pending": pending,
        "result": result,
        "last_error": run.last_error,
        "events": [
            {
                "type": "chat_event",
                "event_id": event.id,
                "run_id": event.run_id,
                "conversation_id": event.conversation_id,
                "event": event.kind,
                "payload": event.payload,
            }
            for event in events
        ],
    }
