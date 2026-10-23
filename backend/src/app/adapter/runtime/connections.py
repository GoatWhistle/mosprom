from app.domain.chat import LlmConnection


class InMemoryLlmConnectionStore:
    def __init__(self) -> None:
        self._connections: dict[str, LlmConnection] = {}

    def put(self, instance_id: str, connection: LlmConnection) -> None:
        self._connections[instance_id] = connection

    def get(self, instance_id: str) -> LlmConnection | None:
        return self._connections.get(instance_id)
