import threading
import unittest

from Brim.execution.errors import OutcomeUnknown
from Brim.slicer.main_thread import MainThread
from tests.test_slicer_adapters import FakeApplication


class QtDeadlineTests(unittest.TestCase):
    def test_expired_queued_callback_does_not_run_later(self):
        app = FakeApplication(deliver=False)
        main = MainThread(app)
        changed, errors = [], []

        def worker():
            try:
                main.call(lambda: changed.append(True), timeout=0.01)
            except OutcomeUnknown as error:
                errors.append(error)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(5)
        app.pending[0]()
        self.assertEqual(len(errors), 1)
        self.assertEqual(changed, [])

    def test_guard_is_checked_when_callback_executes(self):
        app = FakeApplication(deliver=False)
        main = MainThread(app)
        cancelled = threading.Event()
        changed, errors = [], []

        def guard():
            if cancelled.is_set():
                raise RuntimeError("cancelled")

        def worker():
            try:
                main.call(lambda: changed.append(True), guard=guard)
            except RuntimeError as error:
                errors.append(str(error))

        thread = threading.Thread(target=worker)
        thread.start()
        while not app.pending:
            cancelled.wait(0.001)
        cancelled.set()
        app.pending[0]()
        thread.join(5)
        self.assertEqual(errors, ["cancelled"])
        self.assertEqual(changed, [])
