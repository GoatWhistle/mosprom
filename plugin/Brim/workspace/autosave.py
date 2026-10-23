import threading


class Debouncer(object):
    def __init__(self, delay, fire, post, start_timer=None):
        self._delay = delay
        self._fire = fire
        self._post = post
        self._start = start_timer or self._thread_timer
        self._timer = None
        self._lock = threading.Lock()

    @staticmethod
    def _thread_timer(delay, callback):
        timer = threading.Timer(delay, callback)
        timer.daemon = True
        timer.start()
        return timer

    def trigger(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = self._start(self._delay, lambda: self._post(self._fire))

    def cancel(self):
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
