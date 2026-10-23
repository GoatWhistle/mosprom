from collections.abc import Awaitable, Callable

from app.domain.artifacts import REQUIRED_KINDS
from app.domain.run import RunState
from app.usecase.agent_flow import Flow
from app.usecase.config import AgentConfig
from app.usecase.dto.run import RunDTO, TranscriptEntry
from app.usecase.interface.runtime import CallSignals, Clock
from app.usecase.interface.storage import UnitOfWorkFactory
from app.usecase.run_store import RunStore


class ArtifactCompletion:
    def __init__(
        self,
        uow_factory: UnitOfWorkFactory,
        store: RunStore,
        clock: Clock,
        signals: CallSignals,
        config: AgentConfig,
        finish: Callable[[RunDTO], Awaitable[None]],
        fail: Callable[[str, str, str], Awaitable[None]],
    ) -> None:
        self._uow_factory = uow_factory
        self._store = store
        self._clock = clock
        self._signals = signals
        self._config = config
        self._finish = finish
        self._fail = fail

    async def wait(self, run: RunDTO) -> Flow:
        async with self._uow_factory() as uow:
            calls = await uow.tool_calls.list_for_run(run.id)
        sliced = [call for call in calls if call.tool == "slice" and call.scene_version is not None]
        if not sliced or sliced[-1].scene_version is None:
            await self._store.move(run.id, RunState.AGENT_WORKING, "no slice result")
            return Flow.CONTINUE
        scene = sliced[-1].scene_version
        epoch = sliced[-1].scene_epoch
        deadline = self._clock.now().timestamp() + self._config.save_timeout_s
        while True:
            async with self._uow_factory() as uow:
                instance = await uow.instances.get(run.instance_id)
                saved = await uow.artifacts.list_meta(run.id)
            assert instance is not None
            if (instance.scene_epoch, instance.scene_version) != (epoch, scene):
                await self._stale_result(run)
                return Flow.CONTINUE
            kinds = {
                item.kind
                for item in saved
                if (item.scene_epoch, item.scene_version) == (epoch, scene)
            }
            if kinds >= {kind.value for kind in REQUIRED_KINDS}:
                if (instance.scene_epoch, instance.scene_version) == (epoch, scene):
                    await self._finish(run)
                    return Flow.WAIT
                await self._stale_result(run)
                return Flow.CONTINUE
            remaining = deadline - self._clock.now().timestamp()
            if remaining <= 0 or not await self._signals.wait(f"artifacts:{run.id}", remaining):
                await self._fail(
                    run.id, "artifact_timeout", "G-code and 3MF were not saved in time"
                )
                return Flow.WAIT

    async def _stale_result(self, run: RunDTO) -> None:
        note = "[system] The scene changed after slicing, so the saved files are stale. Re-slice."
        await self._store.append(run.id, TranscriptEntry(role="user", content=note))
        await self._store.move(run.id, RunState.AGENT_WORKING, "stale artifacts")
