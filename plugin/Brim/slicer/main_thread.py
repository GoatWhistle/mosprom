import threading

from ..execution.errors import OutcomeUnknown


class MainThread(object):
    def __init__(self, application):
        self._application = application
        self._thread = threading.current_thread()

    def is_main(self):
        return threading.current_thread() is self._thread

    def call(self, function, *args, timeout=120.0, guard=None):
        if self.is_main():
            if guard is not None:
                guard()
            return function(*args)
        done = threading.Event()
        lock = threading.Lock()
        box = {"status": "queued"}

        def run():
            with lock:
                if box["status"] == "revoked":
                    return
                box["status"] = "running"
            try:
                if guard is not None:
                    guard()
                box["value"] = function(*args)
            except BaseException as error:
                box["error"] = error
            finally:
                with lock:
                    box["status"] = "done"
                    done.set()

        self._application.callLater(run)
        if not done.wait(timeout):
            with lock:
                status = box["status"]
                if status == "queued":
                    box["status"] = "revoked"
            if status != "done":
                raise OutcomeUnknown("main thread call timed out (%s)" % status)
        if "error" in box:
            raise box["error"]
        return box.get("value")
