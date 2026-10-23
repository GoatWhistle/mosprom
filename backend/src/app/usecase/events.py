from app.domain.jsonvalue import JsonObject
from app.domain.protocol import CHAT_EVENT
from app.usecase.dto.run import RunDTO
from app.usecase.interface.runtime import Clock, IdGenerator, PluginGateway
from app.usecase.interface.storage import UnitOfWorkFactory


class EventPublisher:
    def __init__(
        self, uow_factory: UnitOfWorkFactory, gateway: PluginGateway, clock: Clock, ids: IdGenerator
    ) -> None:
        self._uow_factory = uow_factory
        self._gateway = gateway
        self._clock = clock
        self._ids = ids

    async def emit(self, run: RunDTO, kind: str, payload: JsonObject) -> None:
        async with self._uow_factory() as uow:
            event = await uow.runs.add_event(
                run.id, run.conversation_id, kind, payload, self._clock.now()
            )
            await uow.commit()
        await self._gateway.send(
            run.instance_id,
            {
                "type": CHAT_EVENT,
                "id": self._ids.new_id(),
                "conversation_id": run.conversation_id,
                "run_id": run.id,
                "event_id": event.id,
                "event": kind,
                "payload": payload,
            },
        )
