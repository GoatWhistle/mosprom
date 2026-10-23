import threading

from ..execution.errors import OutcomeUnknown


class MainThread(object):
    def __init__(self, application):
        self._application = application
        self._thread = threading.current_thread()

    def is_main(self):
        return threading.current_thread() is self._thread

    def call(self, function, *args, timeout=120.0):
        if self.is_main():
            return function(*args)
        done = threading.Event()
        box = {}

        def run():
            try:
                box["value"] = function(*args)
            except BaseException as error:
                box["error"] = error
            finally:
                done.set()

        self._application.callLater(run)
        if not done.wait(timeout):
            raise OutcomeUnknown("main thread did not finish the call within %.0f s" % timeout)
        if "error" in box:
            raise box["error"]
        return box.get("value")
