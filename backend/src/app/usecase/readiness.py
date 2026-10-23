class InstanceReadiness:
    def __init__(self) -> None:
        self._configured: set[str] = set()
        self._snapshots: set[str] = set()
        self._reconciled: set[str] = set()

    def configure(self, instance_id: str) -> None:
        self._configured.add(instance_id)

    def disconnect(self, instance_id: str) -> None:
        self._snapshots.discard(instance_id)
        self._reconciled.discard(instance_id)

    def snapshot(self, instance_id: str) -> None:
        self._snapshots.add(instance_id)

    def reconcile(self, instance_id: str) -> None:
        self._reconciled.add(instance_id)

    def ready(self, instance_id: str) -> bool:
        return all(
            instance_id in items for items in (self._configured, self._snapshots, self._reconciled)
        )
