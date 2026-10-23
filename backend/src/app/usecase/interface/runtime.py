from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Protocol

from app.domain.jsonvalue import JsonObject


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdGenerator(Protocol):
    def new_id(self) -> str: ...

    def new_token(self) -> str: ...


class PluginGateway(Protocol):
    def is_connected(self, instance_id: str) -> bool: ...

    async def send(self, instance_id: str, frame: JsonObject) -> bool: ...


class CallSignals(Protocol):
    def notify(self, key: str) -> None: ...

    async def wait(self, key: str, timeout_s: float) -> bool: ...


class RunScheduler(Protocol):
    def start(self, run_id: str) -> None: ...

    def cancel(self, run_id: str) -> None: ...


type FrameSink = Callable[[JsonObject], Awaitable[None]]


class ConnectionRegistry(Protocol):
    def attach(self, instance_id: str, sink: FrameSink) -> None: ...

    def detach(self, instance_id: str, sink: FrameSink) -> bool: ...
