import asyncio


class AsyncCallSignals:
    def __init__(self) -> None:
        self._events: dict[str, asyncio.Event] = {}

    def notify(self, key: str) -> None:
        self._events.setdefault(key, asyncio.Event()).set()

    async def wait(self, key: str, timeout_s: float) -> bool:
        event = self._events.setdefault(key, asyncio.Event())
        try:
            await asyncio.wait_for(event.wait(), timeout_s)
        except TimeoutError:
            return False
        finally:
            self._events.pop(key, None)
        return True
