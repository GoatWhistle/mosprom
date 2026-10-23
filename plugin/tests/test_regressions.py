import threading
import unittest

from Brim.execution.errors import OutcomeUnknown
from Brim.slicer.main_thread import MainThread
from tests.test_chat import make, event
from tests.test_executor import build, call
from tests.test_slicer_adapters import FakeApplication


class ChatRecoveryTests(unittest.TestCase):
    def test_free_text_answer_is_allowed_without_question_card(self):
        presenter, backend, _, _ = make()
        presenter.send("start")
        presenter.on_chat_event(event("run_state", {"state": "awaiting_user"}, 1))
        presenter.send("more details")
        self.assertEqual(len(backend.sent), 2)

    def test_reconnect_resends_llm_configuration(self):
        presenter, backend, _, _ = make()
        presenter.start()
        backend.llm = None
        presenter.on_status("disconnected")
        presenter.on_status("connected")
        self.assertEqual(backend.llm, ("https://l/v1", "m", "k"))

    def test_reopening_restores_confirmation_and_run(self):
        presenter, backend, _, _ = make()
        presenter.send("start")
        original = backend.get_conversation
        runtime = {"run_id": "run-1", "state": "awaiting_confirmation", "events": [],
                   "pending": {"type": "confirmation", "batch_id": "b", "operations": [{"kind": "arrange"}],
                               "explanation": "arrange"}, "result": None}
        backend.get_conversation = lambda cid: dict(original(cid), runtime=runtime)
        backend.create_conversation_with("ask")
        presenter.open_conversation("c2")
        presenter.open_conversation("c1")
        self.assertEqual(presenter.state.run_id, "run-1")
        self.assertEqual(presenter.state.pending["batch_id"], "b")
        presenter.confirm("accept")
        self.assertEqual(backend.confirmed, [("run-1", "accept", None)])

    def test_reload_restores_downloadable_result(self):
        presenter, backend, _, _ = make()
        presenter.send("start")
        original = backend.get_conversation
        result = {"run_id": "run-1", "summary": {"print_time_seconds": 600},
                  "artifacts": {"gcode": {}, "3mf": {}}}
        backend.get_conversation = lambda cid: dict(original(cid), runtime={
            "run_id": "run-1", "state": "completed", "pending": None, "events": [], "result": result})
        presenter.reload_history()
        self.assertEqual(presenter.state.result, result)
        self.assertFalse(presenter.state.run_active())

    def test_live_event_during_history_request_is_replayed_once(self):
        presenter, backend, _, _ = make()
        presenter.send("start")
        original = backend.get_conversation
        frame = event("question", {"batch_id": "b", "questions": ["Material?"]}, 20)

        def fetch(cid):
            detail = dict(original(cid), runtime={"run_id": "run-1", "state": "agent_working",
                                                 "pending": None, "result": None, "events": []})
            presenter.on_chat_event(frame)
            return detail

        backend.get_conversation = fetch
        presenter.reload_history()
        presenter.on_chat_event(frame)
        self.assertEqual(presenter.state.pending["batch_id"], "b")
        self.assertEqual(len([e for e in presenter.state.entries if e["kind"] == "question"]), 1)

    def test_message_ack_does_not_erase_faster_question_event(self):
        presenter, backend, _, _ = make()
        original = backend.send_message

        def send(*args):
            reply = original(*args)
            presenter.on_chat_event(event("run_state", {"state": "awaiting_user"}, 1))
            presenter.on_chat_event(event("question", {"batch_id": "b", "questions": ["Material?"]}, 2))
            return reply

        backend.send_message = send
        presenter.send("start")
        self.assertEqual(presenter.state.run_state, "awaiting_user")
        self.assertEqual(presenter.state.pending["batch_id"], "b")

    def test_result_is_hidden_until_backend_completes_run(self):
        presenter, _, _, _ = make()
        presenter.send("start")
        presenter.on_tool_result({"run_id": "run-1", "call_id": "s", "ok": True,
                                  "result": {"slice": {"print_time_seconds": 10}}}, "slice")
        self.assertIsNone(presenter.state.result)
        presenter.on_chat_event(event("run_state", {"state": "completed"}, 5))
        self.assertEqual(presenter.state.result["summary"]["print_time_seconds"], 10)


class ExecutionRecoveryTests(unittest.TestCase):
    def test_scene_change_before_slice_handler_prevents_slicing(self):
        executor, port, _, _, _ = build()
        original = executor._tools["slice"]

        def changed(*args):
            port.version += 1
            return original(*args)

        executor._tools["slice"] = changed
        result = executor.execute_call(call("s", "slice", {}, expected=1))
        self.assertEqual(result["error"]["code"], "stale_result")
        self.assertEqual(port.slices, 0)

    def test_slice_result_keeps_exported_revision_after_scene_changes(self):
        executor, port, _, _, _ = build()
        original = executor._tools["slice"]

        def changed(*args):
            result = original(*args)
            port.version += 1
            return result

        executor._tools["slice"] = changed
        result = executor.execute_call(call("s", "slice", {}, expected=1))
        self.assertTrue(result["ok"])
        self.assertEqual(result["scene_version"], 1)
        self.assertEqual(result["result"]["scene_version"], 1)
        self.assertEqual(port.version, 2)

    def test_cancelled_run_never_starts_queued_slice(self):
        executor, port, http, _, _ = build()
        executor.cancel_run("run-1")
        result = executor.execute_call(call("s1", "slice", {}))
        self.assertEqual(result["error"]["code"], "cancelled")
        self.assertEqual(port.slices, 0)
        self.assertEqual(http.calls, [])

    def test_cancelling_another_run_does_not_stop_active_slicer(self):
        executor, port, _, _, _ = build()
        executor._slicing_run = "active"
        executor.cancel_run("older")
        self.assertEqual(port.cancelled, 0)
        executor.cancel_run("active")
        self.assertEqual(port.cancelled, 1)

    def test_different_epoch_rejects_same_version(self):
        executor, port, _, _, _ = build()
        port.scene_epoch = lambda: "new"
        frame = call("a", "apply_changes", {"operations": [{"kind": "arrange"}]}, expected=1)
        frame["expected_scene_epoch"] = "old"
        result = executor.execute_call(frame)
        self.assertEqual(result["error"]["code"], "stale_scene")
        self.assertEqual(port.applied, [])

    def test_cancel_during_slice_prevents_export(self):
        executor, port, http, _, _ = build()
        original = port.slice

        def slice_and_cancel(report, check=None):
            summary = original(report, check)
            executor.cancel_run("run-1")
            return summary

        port.slice = slice_and_cancel
        result = executor.execute_call(call("s", "slice", {}))
        self.assertEqual(result["error"]["code"], "cancelled")
        self.assertEqual(port.exports, 0)
        self.assertEqual(http.calls, [])

    def test_scene_change_during_upload_never_returns_success(self):
        executor, port, http, _, _ = build()
        original = http.upload_artifact_chunk

        def upload(*args):
            receipt = original(*args)
            port.version += 1
            return receipt

        http.upload_artifact_chunk = upload
        result = executor.execute_call(call("s", "slice", {}))
        self.assertEqual(result["error"]["code"], "stale_result")

    def test_retry_keeps_slice_metrics(self):
        executor, port, http, _, _ = build()
        http.fail_upload = 1
        executor.execute_call(call("first", "slice", {}))
        result = executor.execute_call(call("retry", "slice", {}))
        self.assertEqual(result["result"]["slice"]["print_time_seconds"], 600)
        self.assertEqual(port.slices, 1)


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
