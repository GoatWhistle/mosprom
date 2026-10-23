from app.domain.jsonvalue import JsonObject
from app.domain.protocol import TOOL_CALL
from app.usecase.dto.run import RunDTO
from app.usecase.dto.tools import CallStatus, ToolCallDTO
from app.usecase.interface.runtime import CallSignals, Clock, IdGenerator, PluginGateway
from app.usecase.interface.storage import UnitOfWorkFactory


class ToolExecutor:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        gateway: PluginGateway,
        signals: CallSignals,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._uow_factory = uow_factory
        self._gateway = gateway
        self._signals = signals
        self._clock = clock
        self._ids = ids

    async def create(
        self,
        run: RunDTO,
        llm_call_id: str,
        tool: str,
        arguments: JsonObject,
        scene_version: int,
        batch_id: str | None,
    ) -> ToolCallDTO:
        call = ToolCallDTO(
            call_id=self._ids.new_id(),
            run_id=run.id,
            llm_call_id=llm_call_id,
            tool=tool,
            arguments=arguments,
            expected_scene_version=scene_version,
            status=CallStatus.PENDING,
            batch_id=batch_id,
            created_at=self._clock.now(),
        )
        async with self._uow_factory() as uow:
            await uow.tool_calls.add(call)
            await uow.commit()
        return call

    async def run_call(
        self, call: ToolCallDTO, instance_id: str, timeout_s: float
    ) -> ToolCallDTO | None:
        if call.status.finished:
            return call
        async with self._uow_factory() as uow:
            await uow.tool_calls.mark_sent(call.call_id, self._clock.now())
            await uow.commit()
        frame: JsonObject = {
            "type": TOOL_CALL,
            "id": self._ids.new_id(),
            "call_id": call.call_id,
            "run_id": call.run_id,
            "tool": call.tool,
            "arguments": call.arguments,
            "expected_scene_version": call.expected_scene_version,
        }
        if not await self._gateway.send(instance_id, frame):
            return None
        await self._signals.wait(call.call_id, timeout_s)
        stored = await self._load(call.call_id)
        if stored is not None and stored.status.finished:
            return stored
        if not self._gateway.is_connected(instance_id):
            return None
        async with self._uow_factory() as uow:
            await uow.tool_calls.mark_outcome_unknown(call.call_id, self._clock.now())
            await uow.commit()
        return await self._load(call.call_id)

    async def _load(self, call_id: str) -> ToolCallDTO | None:
        async with self._uow_factory() as uow:
            return await uow.tool_calls.get(call_id)
