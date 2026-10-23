import os
import tempfile
import unittest

from Brim.chat.presenter import ChatPresenter
from Brim.chat.state import ChatState
from Brim.protocol.backend_http import BackendHttpError
from Brim.settings import MemoryStore, PluginSettings
from Brim.ui.runner import ImmediateRunner
from Brim.ui.strings import STRINGS


class FakeBackend(object):
    def __init__(self):
        self.conversations = []
        self.messages = {}
        self.sent = []
        self.confirmed = []
        self.stopped = []
        self.uploaded = []
        self.llm = None
        self.fail_with = None
        self.registered = 0
        self.mode_calls = []

    def register(self, instance_id):
        self.registered += 1
        return {"token": "T%d" % self.registered}

    def put_llm(self, base_url, model, api_key):
        self.llm = (base_url, model, api_key)
        return {"status": "configured"}

    def list_conversations(self):
        return {"items": list(self.conversations), "next_cursor": None}

    def create_conversation_with(self, mode):
        item = {"id": "c%d" % (len(self.conversations) + 1), "title": "", "mode": mode, "updated_at": "2026-10-24T10:00:00"}
        self.conversations.insert(0, item)
        self.messages[item["id"]] = []
        return item

    def get_conversation(self, conversation_id):
        conversation = [item for item in self.conversations if item["id"] == conversation_id][0]
        return {"conversation": conversation, "messages": list(self.messages[conversation_id])}

    def put_project(self, conversation_id, state, sha256, active=True):
        self.projects = getattr(self, "projects", [])
        self.projects.append((conversation_id, state, sha256, active))
        return {"project": {"state": state, "version": len(self.projects)}}

    def activate_conversation(self, conversation_id):
        self.activated = getattr(self, "activated", [])
        self.activated.append(conversation_id)
        return {}

    def send_message(self, conversation_id, text, attachment_ids, mode, client_message_id=None):
        if self.fail_with:
            raise self.fail_with
        self.client_ids = getattr(self, "client_ids", [])
        self.client_ids.append(client_message_id)
        self.sent.append((conversation_id, text, list(attachment_ids), mode))
        number = len(self.sent)
        self.messages[conversation_id].append({"id": "m%d" % number, "run_id": "run-%d" % number, "role": "user",
                                               "content": text, "attachment_ids": list(attachment_ids)})
        return {"run_id": "run-%d" % number, "message_id": "m%d" % number}

    def set_mode(self, conversation_id, mode):
        self.mode_calls.append(mode)
        if self.fail_with:
            raise self.fail_with
        return {"id": conversation_id, "mode": mode}

    def confirm(self, run_id, decision, text=None):
        self.confirmed.append((run_id, decision, text))
        return {}

    def stop_run(self, run_id):
        self.stopped.append(run_id)
        return {}

    def upload_attachment(self, name, data):
        self.uploaded.append((name, len(data)))
        return {"id": "att-%d" % len(self.uploaded), "name": name, "size": len(data)}

    def download_artifact(self, run_id, kind):
        return b"DATA-" + kind.encode(), {}

    def health(self):
        return {"status": "ok"}


class FakeBridge(object):
    def __init__(self):
        self.cancelled = []
        self.reconnects = 0

    def cancel_run(self, run_id):
        self.cancelled.append(run_id)

    def reconnect(self):
        self.reconnects += 1


def make(values=None):
    backend = FakeBackend()
    settings = PluginSettings(MemoryStore(dict({"llm_base_url": "https://l/v1", "llm_model": "m", "llm_api_key": "k"}, **(values or {}))))
    changes = []
    presenter = ChatPresenter(backend, settings, ImmediateRunner(), lambda: changes.append(1), bridge=FakeBridge())
    return presenter, backend, settings, changes


def event(kind, payload, event_id, conversation="c1", run="run-1"):
    return {"type": "chat_event", "id": "x%s" % event_id, "conversation_id": conversation, "run_id": run,
            "event_id": event_id, "event": kind, "payload": payload}


class PresenterTests(unittest.TestCase):
    def test_start_registers_pushes_llm_and_opens_latest(self):
        presenter, backend, settings, _ = make()
        backend.create_conversation_with("ask")
        presenter.start()
        self.assertEqual(backend.llm, ("https://l/v1", "m", "k"))
        self.assertEqual(presenter.state.conversation_id, "c1")
        self.assertEqual(settings.token(), "T1")

    def test_send_creates_conversation_and_posts_message(self):
        presenter, backend, _, _ = make()
        presenter.send("PETG bracket")
        self.assertEqual(backend.sent, [("c1", "PETG bracket", [], "ask")])
        self.assertEqual(presenter.state.run_id, "run-1")
        self.assertEqual(presenter.state.entries[0]["kind"], "user")
        self.assertTrue(presenter.state.run_active())

    def test_send_requires_llm_settings(self):
        presenter, backend, _, _ = make({"llm_api_key": ""})
        presenter.send("hello")
        self.assertEqual(backend.sent, [])
        self.assertEqual(presenter.state.notice, STRINGS["ru"]["llm_missing"])

    def test_send_is_blocked_while_run_active_unless_question_pending(self):
        presenter, backend, _, _ = make()
        presenter.send("one")
        presenter.send("two")
        self.assertEqual(len(backend.sent), 1)
        presenter.on_chat_event(event("question", {"batch_id": "b", "questions": ["Material?"]}, 1))
        presenter.on_chat_event(event("run_state", {"state": "awaiting_user"}, 2))
        presenter.send("PETG")
        self.assertEqual(len(backend.sent), 2)

    def test_attachment_flow_uploads_then_sends_ids(self):
        presenter, backend, _, _ = make()
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "part.stl")
        with open(path, "wb") as handle:
            handle.write(b"solid")
        presenter.attach(path)
        self.assertEqual(presenter.state.attachments[0]["id"], "att-1")
        presenter.send("")
        self.assertEqual(backend.sent[0][2], ["att-1"])
        self.assertEqual(presenter.state.attachments, [])
        self.assertEqual(presenter.state.entries[0]["attachments"], ["part.stl"])

    def test_unsupported_attachment_is_rejected_locally(self):
        presenter, backend, _, _ = make()
        presenter.attach("/tmp/model.step")
        self.assertEqual(backend.uploaded, [])
        self.assertIsNotNone(presenter.state.notice)

    def test_confirmation_flow(self):
        presenter, backend, _, _ = make()
        presenter.send("go")
        presenter.on_chat_event(event("confirmation_request", {"batch_id": "b", "operations": [{"kind": "arrange"}], "explanation": "why"}, 1, run="run-1"))
        presenter.on_chat_event(event("run_state", {"state": "awaiting_confirmation"}, 2))
        self.assertEqual(presenter.state.pending["type"], "confirmation")
        presenter.send("")
        self.assertEqual(backend.confirmed, [])
        presenter.send("make it 0.2")
        self.assertEqual(backend.confirmed, [("run-1", "clarify", "make it 0.2")])
        presenter.on_chat_event(event("confirmation_request", {"batch_id": "b2", "operations": [{"kind": "arrange"}]}, 3))
        presenter.confirm("accept")
        self.assertEqual(backend.confirmed[-1], ("run-1", "accept", None))
        confirmation = [e for e in presenter.state.entries if e["kind"] == "confirmation"][-1]
        self.assertEqual(confirmation["decision"], "accept")

    def test_duplicate_events_are_ignored_and_other_chats_filtered(self):
        presenter, _, _, _ = make()
        presenter.send("go")
        frame = event("assistant_message", {"text": "hello"}, 5)
        presenter.on_chat_event(frame)
        presenter.on_chat_event(frame)
        presenter.on_chat_event(event("assistant_message", {"text": "other"}, 6, conversation="c9"))
        texts = [e["text"] for e in presenter.state.entries if e["kind"] == "assistant"]
        self.assertEqual(texts, ["hello"])

    def test_history_reload_does_not_duplicate_messages(self):
        presenter, backend, _, _ = make()
        presenter.send("go")
        presenter.on_chat_event(event("assistant_message", {"text": "hello"}, 5))
        backend.messages["c1"].append({"id": "m9", "run_id": "run-1", "role": "assistant", "content": "hello", "attachment_ids": []})
        presenter.on_chat_event(event("tool_started", {"tool": "slice", "call_id": "k"}, 6))
        presenter.on_status("connected")
        presenter.on_status("disconnected")
        presenter.on_status("connected")
        kinds = [(e["kind"], e.get("text")) for e in presenter.state.entries]
        self.assertEqual(kinds.count(("assistant", "hello")), 1)
        self.assertEqual(kinds.count(("user", "go")), 1)
        self.assertEqual(len([e for e in presenter.state.entries if e["kind"] == "tool"]), 1)

    def test_tool_lifecycle_progress_and_result(self):
        presenter, _, _, _ = make()
        presenter.send("go")
        presenter.on_chat_event(event("tool_started", {"tool": "slice", "call_id": "k1"}, 1))
        presenter.on_progress({"call_id": "k1", "stage": "slicing", "fraction": 0.5})
        self.assertEqual(presenter.state.progress["fraction"], 0.5)
        frame = {"call_id": "k1", "run_id": "run-1", "ok": True, "result": {"slice": {"print_time_seconds": 600}, "artifacts": {}}, "applied": []}
        presenter.on_tool_result(frame, "slice")
        presenter.on_chat_event(event("tool_finished", {"tool": "slice", "call_id": "k1", "ok": True, "error": None}, 2))
        presenter.on_chat_event(event("run_state", {"state": "completed"}, 3))
        tool = [e for e in presenter.state.entries if e["kind"] == "tool"][0]
        self.assertEqual(tool["status"], "ok")
        self.assertEqual(presenter.state.result["summary"]["print_time_seconds"], 600)
        self.assertIsNone(presenter.state.progress)
        self.assertFalse(presenter.state.run_active())

    def test_failed_tool_detail_shows_error(self):
        presenter, _, _, _ = make()
        presenter.send("go")
        presenter.on_chat_event(event("tool_started", {"tool": "apply_changes", "call_id": "k1"}, 1))
        frame = {"call_id": "k1", "run_id": "run-1", "ok": False, "error": {"code": "stale_scene", "message": "changed"}, "applied": []}
        presenter.on_tool_result(frame, "apply_changes")
        tool = [e for e in presenter.state.entries if e["kind"] == "tool"][0]
        self.assertIn("stale_scene", tool["detail"])

    def test_stop_aborts_backend_and_cancels_plugin_queue(self):
        presenter, backend, _, _ = make()
        presenter.send("go")
        presenter.stop()
        self.assertEqual(backend.stopped, ["run-1"])
        self.assertEqual(presenter._bridge.cancelled, ["run-1"])
        self.assertFalse(presenter.state.run_active())

    def test_mode_change_rolls_back_on_failure(self):
        presenter, backend, _, _ = make()
        presenter.new_conversation()
        presenter.set_mode("auto")
        self.assertEqual(presenter.state.mode, "auto")
        backend.fail_with = BackendHttpError("nope", 500)
        presenter.set_mode("ask")
        self.assertEqual(presenter.state.mode, "auto")
        self.assertIn("nope", presenter.state.notice)

    def test_backend_error_becomes_notice(self):
        presenter, backend, _, _ = make()
        presenter.new_conversation()
        backend.fail_with = BackendHttpError("HTTP 409: run_active", 409)
        presenter.send("go")
        self.assertIn("run_active", presenter.state.notice)
        self.assertEqual(presenter.state.entries, [])
        self.assertFalse(presenter.state.busy)

    def test_unauthorized_reregisters_once(self):
        presenter, backend, settings, _ = make()
        presenter.new_conversation()
        calls = {"n": 0}
        original = backend.send_message

        def flaky(*args):
            calls["n"] += 1
            if calls["n"] == 1:
                raise BackendHttpError("HTTP 401", 401)
            return original(*args)

        backend.send_message = flaky
        presenter.send("go")
        self.assertEqual(len(backend.sent), 1)
        self.assertEqual(backend.registered, 2)
        self.assertEqual(backend.llm, ("https://l/v1", "m", "k"))

    def test_save_artifact_writes_file(self):
        presenter, _, _, _ = make()
        presenter.send("go")
        target = os.path.join(tempfile.mkdtemp(), "out.gcode")
        presenter.save_artifact("gcode", target)
        with open(target, "rb") as handle:
            self.assertEqual(handle.read(), b"DATA-gcode")

    def test_settings_apply_pushes_llm_and_reconnects_on_backend_change(self):
        presenter, backend, settings, _ = make()
        self.assertTrue(presenter.apply_settings("http://other:9000", "https://n/v1", "m2", "key2", "en", "light"))
        self.assertEqual(backend.llm, ("https://n/v1", "m2", "key2"))
        self.assertEqual(presenter._bridge.reconnects, 1)
        self.assertEqual((settings.language(), settings.theme()), ("en", "light"))
        self.assertFalse(presenter.apply_settings("bad", "", "", "", "ru", "dark"))
        self.assertIsNotNone(presenter.view()["settings_notice"])

    def test_view_never_exposes_the_api_key(self):
        presenter, _, _, _ = make()
        text = repr(presenter.view())
        self.assertNotIn("'k'", text)
        self.assertTrue(presenter.view()["settings"]["llm_key_saved"])

    def test_dictionaries_have_the_same_keys(self):
        self.assertEqual(sorted(STRINGS["ru"]), sorted(STRINGS["en"]))


class StateTests(unittest.TestCase):
    def test_error_event_marks_run_failed(self):
        state = ChatState()
        state.select_conversation("c1", "ask")
        state.apply_chat_event(event("error", {"code": "llm_down", "message": "x"}, 1))
        self.assertEqual(state.run_state, "failed")
        self.assertEqual(state.entries[-1]["kind"], "error")


if __name__ == "__main__":
    unittest.main()
