import asyncio
from collections.abc import Callable, Coroutine


class AsyncioRunScheduler:
    def __init__(self, runner: Callable[[str], Coroutine[None, None, None]]) -> None:
        self._runner = runner
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._again: set[str] = set()
        self._closed = False

    def start(self, run_id: str) -> None:
        if self._closed:
            return
        current = self._tasks.get(run_id)
        if current is not None and not current.done():
            self._again.add(run_id)
            return
        task = asyncio.create_task(self._runner(run_id))
        self._tasks[run_id] = task
        task.add_done_callback(lambda done: self._forget(run_id, done))

    def cancel(self, run_id: str) -> None:
        self._again.discard(run_id)
        task = self._tasks.get(run_id)
        if task is not None and not task.done():
            task.cancel()

    async def aclose(self) -> None:
        self._closed = True
        self._again.clear()
        tasks = [task for task in self._tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    def _forget(self, run_id: str, done: asyncio.Task[None]) -> None:
        if self._tasks.get(run_id) is done:
            del self._tasks[run_id]
            if run_id in self._again:
                self._again.discard(run_id)
                self.start(run_id)
