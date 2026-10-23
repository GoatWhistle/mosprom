import queue
import threading


class ThreadRunner(object):
    def __init__(self, deliver):
        self._deliver = deliver
        self._queue = queue.Queue()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def submit(self, work, done):
        self._queue.put((work, done))

    def stop(self):
        self._queue.put(None)

    def _loop(self):
        while True:
            item = self._queue.get()
            if item is None:
                return
            work, done = item
            try:
                value, error = work(), None
            except Exception as failure:
                value, error = None, failure
            self._deliver(lambda value=value, error=error, done=done: done(value, error))


class ImmediateRunner(object):
    def submit(self, work, done):
        try:
            value, error = work(), None
        except Exception as failure:
            value, error = None, failure
        done(value, error)
