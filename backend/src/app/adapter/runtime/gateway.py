from app.domain.jsonvalue import JsonObject
from app.usecase.interface.runtime import FrameSink


class InstanceGateway:
    def __init__(self) -> None:
        self._sinks: dict[str, FrameSink] = {}

    def attach(self, instance_id: str, sink: FrameSink) -> None:
        self._sinks[instance_id] = sink

    def detach(self, instance_id: str, sink: FrameSink) -> bool:
        if self._sinks.get(instance_id) is sink:
            del self._sinks[instance_id]
            return True
        return False

    def is_connected(self, instance_id: str) -> bool:
        return instance_id in self._sinks

    async def send(self, instance_id: str, frame: JsonObject) -> bool:
        sink = self._sinks.get(instance_id)
        if sink is None:
            return False
        try:
            await sink(frame)
        except Exception:  # noqa: BLE001 - any sink failure means the connection is gone
            self.detach(instance_id, sink)
            return False
        return True
