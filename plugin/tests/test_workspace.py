import os
import tempfile
import unittest
import zipfile
from unittest import mock

from Brim.chat.entries_view import agent_status, group_entries
from Brim.chat.presenter import ChatPresenter
from Brim.chat.view import chat_view
from Brim.execution.errors import OperationError
from Brim.protocol.backend_http import BackendHttpError
from Brim.settings import MemoryStore, PluginSettings
from Brim.slicer.port import SlicerPort
from Brim.slicer.project_archive import verify_workspace
from Brim.ui.runner import ImmediateRunner
from Brim.ui.strings import STRINGS
from Brim.workspace.autosave import Debouncer
from Brim.workspace.service import WorkspaceError, WorkspaceService
from Brim.workspace.store import WorkspaceStore
from tests.test_chat import FakeBackend, FakeBridge, event

T = STRINGS["ru"]


class WorkspacePort(object):
    def __init__(self):
        self.scene = []
        self.locked = False
        self.lock_log = []
        self.fail_save = False
        self.fail_load = False

    def lock_changes(self, locked):
        self.locked = locked
        self.lock_log.append(locked)

    def scene_is_empty(self):
        return not self.scene

    def save_workspace(self, path):
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("3D/3dmodel.model", "<model>%s</model>" % ",".join(self.scene))
        if self.fail_save:
            with open(path, "wb") as handle:
                handle.write(b"torn")
            raise IOError("disk full")

    def load_workspace(self, path):
        verify_workspace(path)
        if self.fail_load:
            raise IOError("loader crashed")
        with zipfile.ZipFile(path) as archive:
            text = archive.read("3D/3dmodel.model").decode("utf-8")[7:-8]
        self.scene = [item for item in text.split(",") if item]

    def clear_workspace(self):
        self.scene = []


class PortLockTests(unittest.TestCase):
    def make(self):
        scene_ops = mock.Mock()
        scene_ops.count.return_value = 0
        slicing = mock.Mock()
        port = SlicerPort(mock.Mock(), mock.Mock(), mock.Mock(), scene_ops, mock.Mock(), mock.Mock(), slicing,
                          mock.Mock(), mock.Mock(), mock.Mock())
        return port, scene_ops, slicing

    def test_locked_port_rejects_edits_and_slicing(self):
        port, scene_ops, slicing = self.make()
        port.lock_changes(True)
        with self.assertRaises(OperationError):
            port.apply_operation({"kind": "arrange"})
        with self.assertRaises(OperationError):
            port.slice(lambda *args: None)
        slicing.slice.assert_not_called()
        port.lock_changes(False)
        port.slice(lambda *args: None)
        slicing.slice.assert_called_once()

    def test_empty_scene_and_clear_go_through_scene_operations(self):
        port, scene_ops, _ = self.make()
        self.assertTrue(port.scene_is_empty())
        port.clear_workspace()
        scene_ops.clear.assert_called_once_with()

    def test_load_rejects_corrupt_archive_before_touching_scene(self):
        port, scene_ops, _ = self.make()
        path = os.path.join(tempfile.mkdtemp(), "x.3mf")
        with open(path, "wb") as handle:
            handle.write(b"junk")
        with self.assertRaises(OperationError):
            port.load_workspace(path)
        scene_ops.open_3mf.assert_not_called()


class ManualTimer(object):
    def __init__(self, delay, callback):
        self.callback = callback
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


def build():
    directory = tempfile.mkdtemp()
    backend = FakeBackend()
    port = WorkspacePort()
    store = WorkspaceStore(os.path.join(directory, "ws"))
    service = WorkspaceService(port, store)
    settings = PluginSettings(MemoryStore({"llm_base_url": "https://l/v1", "llm_model": "m", "llm_api_key": "k"}))
    presenter = ChatPresenter(backend, settings, ImmediateRunner(), lambda: None, bridge=FakeBridge(), workspace=service)
    return presenter, backend, port, store


def two_projects():
    presenter, backend, port, store = build()
    presenter.new_conversation()
    port.scene = ["bracket"]
    presenter.new_conversation()
    return presenter, backend, port, store


class StoreTests(unittest.TestCase):
    def test_corrupt_index_is_treated_as_empty(self):
        store = WorkspaceStore(tempfile.mkdtemp())
        with open(os.path.join(store._directory, "index.json"), "w") as handle:
            handle.write("{broken")
        self.assertEqual(store.status("c1"), "none")
        self.assertIsNone(store.active())

    def test_missing_file_means_no_project(self):
        store = WorkspaceStore(tempfile.mkdtemp())
        with open(store.temp_path("c1"), "w") as handle:
            handle.write("x")
        store.commit("c1")
        self.assertEqual(store.status("c1"), "saved")
        os.remove(store.path_for("c1"))
        self.assertEqual(store.status("c1"), "none")


class ServiceTests(unittest.TestCase):
    def test_failed_save_keeps_last_good_copy(self):
        port = WorkspacePort()
        service = WorkspaceService(port, WorkspaceStore(tempfile.mkdtemp()))
        port.scene = ["a"]
        service.save("c1")
        port.scene = ["a", "b"]
        port.fail_save = True
        with self.assertRaises(WorkspaceError):
            service.save("c1")
        port.fail_save = False
        port.scene = []
        service.open("c1")
        self.assertEqual(port.scene, ["a"])
        self.assertFalse(os.path.exists(service.store.temp_path("c1")))

    def test_empty_scene_is_saved_as_empty_project(self):
        port = WorkspacePort()
        service = WorkspaceService(port, WorkspaceStore(tempfile.mkdtemp()))
        self.assertEqual(service.save("c1"), "empty")
        port.scene = ["x"]
        service.open("c1")
        self.assertEqual(port.scene, [])

    def test_corrupt_project_is_reported_not_loaded(self):
        port = WorkspacePort()
        service = WorkspaceService(port, WorkspaceStore(tempfile.mkdtemp()))
        port.scene = ["a"]
        service.save("c1")
        with open(service.store.path_for("c1"), "wb") as handle:
            handle.write(b"garbage")
        port.scene = ["keep"]
        with self.assertRaises(WorkspaceError):
            service.open("c1")
        self.assertEqual(port.scene, ["keep"])


class SwitchingTests(unittest.TestCase):
    def test_each_chat_gets_its_own_scene_and_new_chat_starts_empty(self):
        presenter, _, port, _ = two_projects()
        self.assertEqual(port.scene, [])
        port.scene = ["lid"]
        presenter.open_conversation("c1")
        self.assertEqual(port.scene, ["bracket"])
        port.scene = ["bracket", "hand-edit"]
        presenter.open_conversation("c2")
        self.assertEqual(port.scene, ["lid"])
        presenter.open_conversation("c1")
        self.assertEqual(port.scene, ["bracket", "hand-edit"])
        self.assertIsNone(presenter.state.switching)
        self.assertEqual(port.lock_log[-1], False)

    def test_scene_is_locked_for_the_whole_switch(self):
        presenter, _, port, _ = two_projects()
        presenter.open_conversation("c1")
        self.assertEqual(port.lock_log[-2:], [True, False])

    def test_new_project_from_current_scene_keeps_models(self):
        presenter, _, port, store = build()
        presenter.new_conversation()
        port.scene = ["part"]
        presenter.new_conversation(from_scene=True)
        self.assertEqual(presenter.state.conversation_id, "c2")
        self.assertEqual(port.scene, ["part"])
        self.assertEqual(store.status("c2"), "saved")
        self.assertEqual(store.status("c1"), "saved")

    def test_save_failure_keeps_current_project_and_offers_retry(self):
        presenter, _, port, _ = two_projects()
        port.scene = ["lid"]
        port.fail_save = True
        presenter.open_conversation("c1")
        self.assertEqual(presenter.state.conversation_id, "c2")
        self.assertEqual(port.scene, ["lid"])
        self.assertIn(T["switch_save_failed"], presenter.state.notice)
        self.assertTrue(presenter.state.switch_retry is not None)
        port.fail_save = False
        presenter.retry_switch()
        self.assertEqual(presenter.state.conversation_id, "c1")
        self.assertEqual(port.scene, ["bracket"])

    def test_open_failure_restores_previous_project(self):
        presenter, _, port, store = two_projects()
        port.scene = ["lid"]
        with open(store.path_for("c1"), "wb") as handle:
            handle.write(b"garbage")
        presenter.open_conversation("c1")
        self.assertEqual(presenter.state.conversation_id, "c2")
        self.assertEqual(port.scene, ["lid"])
        self.assertIn(T["switch_open_restored"], presenter.state.notice)
        self.assertFalse(presenter.state.workspace_blocked)

    def test_double_failure_blocks_agent_and_recovery_unblocks(self):
        presenter, backend, port, store = two_projects()
        port.scene = ["lid"]
        port.fail_load = True
        presenter.open_conversation("c1")
        self.assertTrue(presenter.state.workspace_blocked)
        self.assertTrue(port.locked)
        presenter.send("hello")
        self.assertEqual(backend.sent, [])
        port.fail_load = False
        presenter.recover_workspace()
        self.assertFalse(presenter.state.workspace_blocked)
        self.assertFalse(port.locked)
        self.assertEqual(port.scene, ["lid"])

    def test_running_agent_asks_before_switching(self):
        presenter, backend, port, _ = two_projects()
        presenter.send("go")
        presenter.open_conversation("c1")
        self.assertEqual(presenter.state.conversation_id, "c2")
        self.assertIsNotNone(presenter.state.switch_prompt)
        presenter.cancel_switch()
        self.assertIsNone(presenter.state.switch_prompt)
        presenter.open_conversation("c1")
        presenter.stop_and_switch()
        self.assertEqual(backend.stopped, ["run-1"])
        self.assertEqual(presenter.state.conversation_id, "c1")

    def test_waiting_for_the_user_does_not_block_switching(self):
        presenter, _, _, _ = two_projects()
        presenter.send("go")
        presenter.on_chat_event(event("question", {"batch_id": "b", "questions": ["?"]}, 1, conversation="c2"))
        presenter.on_chat_event(event("run_state", {"state": "awaiting_user"}, 2, conversation="c2"))
        presenter.open_conversation("c1")
        self.assertEqual(presenter.state.conversation_id, "c1")

    def test_late_event_of_previous_chat_is_ignored(self):
        presenter, _, _, _ = two_projects()
        presenter.open_conversation("c1")
        presenter.on_chat_event(event("assistant_message", {"text": "late"}, 5, conversation="c2"))
        self.assertEqual([item for item in presenter.state.entries if item["text"] == "late"], [])

    def test_restart_restores_active_project(self):
        presenter, backend, port, store = two_projects()
        port.scene = ["lid"]
        presenter.open_conversation("c1")
        settings = presenter._settings
        fresh = ChatPresenter(backend, settings, ImmediateRunner(), lambda: None, bridge=FakeBridge(),
                              workspace=WorkspaceService(port, store))
        port.scene = []
        fresh.start()
        self.assertEqual(fresh.state.conversation_id, "c1")
        self.assertEqual(port.scene, ["bracket"])
        self.assertFalse(port.locked)


class DraftTests(unittest.TestCase):
    def test_drafts_and_attachments_stay_with_their_chat(self):
        presenter, _, _, _ = two_projects()
        presenter.set_draft("second chat text")
        presenter.state.attachments.append({"id": "a", "name": "x.stl", "size": 1})
        presenter.open_conversation("c1")
        self.assertEqual(presenter.state.draft, "")
        self.assertEqual(presenter.state.attachments, [])
        presenter.set_draft("first")
        presenter.open_conversation("c2")
        self.assertEqual(presenter.state.draft, "second chat text")
        self.assertEqual(presenter.state.attachments[0]["name"], "x.stl")

    def test_failed_send_keeps_text_and_retry_sends_once(self):
        presenter, backend, _, _ = two_projects()
        presenter.set_draft("hello")
        backend.fail_with = BackendHttpError("down")
        presenter.send("hello")
        self.assertEqual(presenter.state.draft, "hello")
        self.assertEqual(presenter.state.entries, [])
        backend.fail_with = None
        presenter.send("hello")
        self.assertEqual(len(backend.sent), 1)
        self.assertEqual(presenter.state.draft, "")
        self.assertEqual(len(presenter.state.entries), 1)


class AutosaveTests(unittest.TestCase):
    def test_scene_change_marks_dirty_then_saves_after_delay(self):
        presenter, _, port, store = two_projects()
        timers = []
        presenter._autosave._debounce = Debouncer(
            1.0, presenter._autosave.save_now, lambda function: function(),
            lambda delay, callback: timers.append(ManualTimer(delay, callback)) or timers[-1])
        port.scene = ["lid", "more"]
        presenter.on_scene_changed()
        presenter.on_scene_changed()
        self.assertEqual(presenter.state.save_state, "dirty")
        self.assertTrue(timers[0].cancelled)
        timers[-1].callback()
        self.assertEqual(presenter.state.save_state, "saved")
        port.scene = []
        presenter._workspace.open("c2")
        self.assertEqual(port.scene, ["lid", "more"])

    def test_failed_autosave_is_reported(self):
        presenter, _, port, _ = two_projects()
        port.scene = ["lid"]
        port.fail_save = True
        presenter._autosave.save_now()
        self.assertEqual(presenter.state.save_state, "failed")
        self.assertIn(T["save_failed"], presenter.state.notice)

    def test_changes_during_switch_are_not_autosaved(self):
        presenter, _, _, _ = two_projects()
        presenter.state.switching = "opening"
        presenter.state.save_state = "saved"
        presenter.on_scene_changed()
        self.assertEqual(presenter.state.save_state, "saved")

    def test_flush_saves_pending_changes(self):
        presenter, _, port, store = two_projects()
        port.scene = ["lid"]
        presenter.on_scene_changed()
        presenter.flush_workspace()
        self.assertEqual(presenter.state.save_state, "saved")
        self.assertEqual(store.status("c2"), "saved")


class ProjectSyncTests(unittest.TestCase):
    def test_saves_are_recorded_in_backend_and_switching_activates_target(self):
        presenter, backend, port, store = two_projects()
        port.scene = ["lid"]
        presenter.open_conversation("c1")
        saved = [item for item in backend.projects if item[0] == "c2"]
        self.assertEqual(saved[-1][1], "saved")
        self.assertEqual(saved[-1][2], store.digest("c2"))
        self.assertFalse(saved[-1][3])
        self.assertEqual(backend.activated[-1], "c1")

    def test_autosave_reports_version_and_marks_result_stale(self):
        presenter, backend, port, _ = two_projects()
        state = presenter.state
        state.result = {"run_id": "r", "project_version": 1, "summary": {}}
        port.scene = ["lid"]
        presenter._autosave.save_now()
        self.assertEqual(state.project_version, len(backend.projects))
        view = chat_view(state, presenter._settings, None, None)
        self.assertEqual(view["result_stale"], state.project_version > 1)
        state.result["project_version"] = state.project_version
        self.assertFalse(chat_view(state, presenter._settings, None, None)["result_stale"])

    def test_backend_failure_does_not_lose_local_save(self):
        presenter, backend, port, store = two_projects()
        backend.put_project = lambda *args, **kwargs: (_ for _ in ()).throw(BackendHttpError("down"))
        port.scene = ["lid"]
        presenter._autosave.save_now()
        self.assertEqual(store.status("c2"), "saved")
        self.assertEqual(presenter.state.notice, T["project_link_failed"])


class ClientIdTests(unittest.TestCase):
    def test_retry_keeps_id_and_edit_changes_it(self):
        presenter, backend, _, _ = two_projects()
        presenter.set_draft("hello")
        backend.fail_with = BackendHttpError("down")
        presenter.send("hello")
        first = presenter.state.client_message_id
        presenter.send("hello")
        self.assertEqual(presenter.state.client_message_id, first)
        presenter.set_draft("hello again")
        self.assertIsNone(presenter.state.client_message_id)
        backend.fail_with = None
        presenter.send("hello again")
        self.assertEqual(len(backend.client_ids), 1)
        self.assertIsNone(presenter.state.client_message_id)


class ViewTests(unittest.TestCase):
    def base(self, **values):
        data = {"switching": None, "workspace_blocked": False, "connection": "connected", "run_state": None,
                "run_active": False, "entries": []}
        data.update(values)
        return data

    def test_offline_never_claims_agent_activity(self):
        kind, text = agent_status(self.base(connection="disconnected", run_state="interviewing", run_active=True), T, True)
        self.assertEqual(kind, "error")
        self.assertEqual(text, T["status_offline"])

    def test_running_tool_names_the_stage(self):
        entries = [{"kind": "tool", "tool": "slice", "status": "running", "key": "k1"}]
        _, text = agent_status(self.base(run_state="executing_tool", run_active=True, entries=entries), T, True)
        self.assertEqual(text, T["tool_active_slice"])

    def test_switching_has_priority(self):
        _, text = agent_status(self.base(switching="saving", connection="disconnected"), T, True)
        self.assertEqual(text, T["status_saving_project"])

    def test_completed_tools_are_grouped_but_failures_stay_visible(self):
        entries = [{"kind": "tool", "status": "ok", "key": "k1"}, {"kind": "tool", "status": "ok", "key": "k2"},
                   {"kind": "tool", "status": "failed", "key": "k3"}, {"kind": "tool", "status": "ok", "key": "k4"}]
        grouped = group_entries(entries)
        self.assertEqual([item["kind"] for item in grouped], ["tool_group", "tool", "tool"])
        self.assertEqual(len(grouped[0]["items"]), 2)


if __name__ == "__main__":
    unittest.main()
