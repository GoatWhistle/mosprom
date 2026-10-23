import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.chat import LlmConnection
from app.domain.errors import (
    ContractMismatch,
    InstanceExists,
    InvalidRequest,
    NotFound,
    Unauthorized,
)
from app.domain.jsonvalue import JsonObject
from app.domain.protocol import CONTRACT_VERSION
from app.usecase.dto.instance import InstanceDTO
from app.usecase.dto.tools import ToolOutcome
from app.usecase.interface.llm import LlmConnectionStore
from app.usecase.interface.runtime import CallSignals, Clock, IdGenerator
from app.usecase.interface.storage import UnitOfWorkFactory


@dataclass(frozen=True, slots=True)
class HelloResult:
    instance: InstanceDTO
    pending_calls: tuple[str, ...]


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class InstanceService:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        connections: LlmConnectionStore,
        signals: CallSignals,
        clock: Clock,
        ids: IdGenerator,
    ) -> None:
        self._uow_factory = uow_factory
        self._connections = connections
        self._signals = signals
        self._clock = clock
        self._ids = ids

    async def register(self, instance_id: str) -> str:
        if not instance_id.strip():
            raise InvalidRequest("instance_id is required")
        token = self._ids.new_token()
        async with self._uow_factory() as uow:
            if not await uow.instances.create(instance_id, hash_token(token), self._clock.now()):
                raise InstanceExists()
            await uow.commit()
        return token

    async def authenticate(self, token: str | None) -> InstanceDTO:
        if not token:
            raise Unauthorized()
        async with self._uow_factory() as uow:
            instance = await uow.instances.get_by_token_hash(hash_token(token))
        if instance is None:
            raise Unauthorized()
        return instance

    def set_llm(self, instance_id: str, base_url: str, model: str, api_key: str) -> None:
        if not base_url.strip() or not model.strip() or not api_key.strip():
            raise InvalidRequest("base_url, model and api_key are required")
        self._connections.put(
            instance_id,
            LlmConnection(base_url=base_url.strip(), model=model.strip(), api_key=api_key),
        )

    async def hello(
        self,
        instance_id: str,
        *,
        contract_version: str,
        slicer_version: str,
        modes: Sequence[str],
        printer: JsonObject,
    ) -> HelloResult:
        if contract_version != CONTRACT_VERSION:
            raise ContractMismatch()
        async with self._uow_factory() as uow:
            await uow.instances.record_hello(
                instance_id,
                slicer_version=slicer_version,
                modes=modes,
                printer=printer,
                contract_version=contract_version,
                now=self._clock.now(),
            )
            instance = await uow.instances.get(instance_id)
            unfinished = await uow.tool_calls.list_unfinished_for_instance(instance_id)
            await uow.commit()
        if instance is None:
            raise NotFound()
        return HelloResult(instance, tuple(call.call_id for call in unfinished))

    async def record_snapshot(
        self, instance_id: str, scene_version: int, state: JsonObject
    ) -> bool:
        async with self._uow_factory() as uow:
            stored = await uow.instances.record_snapshot(
                instance_id, scene_version, state, self._clock.now()
            )
            await uow.commit()
        return stored

    async def reconcile(self, instance_id: str, plugin_pending: Sequence[str]) -> list[str]:
        known = set(plugin_pending)
        async with self._uow_factory() as uow:
            unfinished = await uow.tool_calls.list_unfinished_for_instance(instance_id)
            resumed = []
            for call in unfinished:
                if call.status.value == "sent" and call.call_id not in known:
                    await uow.tool_calls.mark_outcome_unknown(call.call_id, self._clock.now())
                resumed.append(call.run_id)
            await uow.commit()
        return sorted(set(resumed))

    async def record_tool_result(self, instance_id: str, outcome: ToolOutcome) -> bool:
        async with self._uow_factory() as uow:
            call = await uow.tool_calls.get(outcome.call_id)
            if call is None:
                raise NotFound("Unknown tool call")
            run = await uow.runs.get(call.run_id)
            if run is None or run.instance_id != instance_id:
                raise NotFound("Unknown tool call")
            stored = await uow.tool_calls.complete(outcome, self._clock.now())
            if stored and outcome.scene_version is not None:
                await uow.instances.advance_scene_version(instance_id, outcome.scene_version)
            await uow.commit()
        self._signals.notify(outcome.call_id)
        return stored
