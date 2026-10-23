from app.domain.confirmation import Mode
from app.domain.errors import DomainError, InvalidRequest
from app.domain.jsonvalue import JsonObject, JsonValue
from app.domain.protocol import (
    HELLO_ACK,
    PROGRESS,
    PROTOCOL_ERROR,
)
from app.usecase.dto.tools import ToolOutcome
from app.usecase.instances import InstanceService
from app.usecase.interface.runtime import Clock, IdGenerator
from app.usecase.interface.storage import UnitOfWorkFactory
from app.usecase.runs import RunService


class PluginSession:
    def __init__(
        self,
        instances: InstanceService,
        runs: RunService,
        uow_factory: UnitOfWorkFactory,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._instances = instances
        self._runs = runs
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids

    async def handle(self, instance_id: str, frame: JsonObject) -> list[JsonObject]:
        try:
            return await self._dispatch(instance_id, frame)
        except DomainError as exc:
            return [self._error(frame, exc.code, exc.message)]

    async def _dispatch(self, instance_id: str, frame: JsonObject) -> list[JsonObject]:
        match frame.get("type"):
            case "hello":
                return await self._hello(instance_id, frame)
            case "state_snapshot":
                scene = _int(frame, "scene_version")
                state = frame.get("state")
                if not isinstance(state, dict):
                    raise InvalidRequest("state must be an object")
                await self._instances.record_snapshot(instance_id, scene, state)
                return []
            case "chat_message":
                return await self._chat(instance_id, frame)
            case "tool_result":
                await self._instances.record_tool_result(instance_id, _outcome(frame))
                return []
            case "pending_calls":
                await self._pending(instance_id, frame)
                return []
            case "progress":
                await self._progress(instance_id, frame)
                return []
            case "mcp_response":
                return []
        raise InvalidRequest(f"Unknown frame type {frame.get('type')!r}")

    async def _hello(self, instance_id: str, frame: JsonObject) -> list[JsonObject]:
        modes = frame.get("modes")
        printer = frame.get("printer")
        result = await self._instances.hello(
            instance_id,
            contract_version=str(frame.get("contract_version", "")),
            slicer_version=str(frame.get("slicer_version", "")),
            modes=[str(item) for item in modes] if isinstance(modes, list) else [],
            printer=printer if isinstance(printer, dict) else {},
        )
        pending: list[JsonValue] = list(result.pending_calls)
        return [
            {
                "type": HELLO_ACK,
                "id": str(frame.get("id", self._ids.new_id())),
                "instance_id": instance_id,
                "pending_calls": pending,
            }
        ]

    async def _chat(self, instance_id: str, frame: JsonObject) -> list[JsonObject]:
        attachments = frame.get("attachment_ids")
        mode = frame.get("mode")
        await self._runs.post_message(
            instance_id,
            str(frame.get("conversation_id", "")),
            str(frame.get("text", "")),
            tuple(str(item) for item in attachments) if isinstance(attachments, list) else (),
            Mode(mode) if isinstance(mode, str) and mode in {"auto", "ask"} else None,
        )
        return []

    async def _pending(self, instance_id: str, frame: JsonObject) -> None:
        raw = frame.get("call_ids")
        known = [str(item) for item in raw] if isinstance(raw, list) else []
        await self._instances.reconcile(instance_id, known)
        await self._runs.resume_instance(instance_id)

    async def _progress(self, instance_id: str, frame: JsonObject) -> None:
        call_id = str(frame.get("call_id", ""))
        async with self._uow_factory() as uow:
            call = await uow.tool_calls.get(call_id)
            if call is None:
                return
            run = await uow.runs.get(call.run_id)
            if run is None or run.instance_id != instance_id:
                return
            await uow.runs.add_event(
                run.id,
                run.conversation_id,
                PROGRESS,
                {
                    "call_id": call_id,
                    "stage": frame.get("stage"),
                    "fraction": frame.get("fraction"),
                },
                self._clock.now(),
            )
            await uow.commit()

    def _error(self, frame: JsonObject, code: str, message: str) -> JsonObject:
        return {
            "type": PROTOCOL_ERROR,
            "id": str(frame.get("id", self._ids.new_id())),
            "code": code,
            "message": message,
        }


def _int(frame: JsonObject, name: str) -> int:
    value = frame.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidRequest(f"{name} must be an integer")
    return value


def _outcome(frame: JsonObject) -> ToolOutcome:
    call_id = frame.get("call_id")
    if not isinstance(call_id, str):
        raise InvalidRequest("call_id is required")
    result = frame.get("result")
    error = frame.get("error")
    applied = frame.get("applied")
    scene = frame.get("scene_version")
    return ToolOutcome(
        call_id=call_id,
        ok=frame.get("ok") is True,
        scene_version=scene if isinstance(scene, int) and not isinstance(scene, bool) else None,
        result=result if isinstance(result, dict) else {},
        error=error if isinstance(error, dict) else None,
        applied=tuple(item for item in applied if isinstance(item, dict))
        if isinstance(applied, list)
        else (),
    )
