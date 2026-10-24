import os
import tempfile
import unittest
from unittest import mock

from tests.chat_fakes import ChatPresenter, FakeHub, FakeLlm, FakeLoop, ImmediateRunner, WorkspacePort, \
    build, two_projects
from Brim.execution.errors import OperationError
from Brim.slicer.port import SlicerPort
from Brim.ui.strings import STRINGS
from Brim.workspace.autosave import Debouncer
from Brim.workspace.service import WorkspaceError, WorkspaceService
from Brim.workspace.store import WorkspaceStore

T = STRINGS["ru"]


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


class StoreTests(unittest.TestCase):
    def test_corrupt_index_is_treated_as_empty(self):
        store = WorkspaceStore(tempfile.mkdtemp())
        with open(os.path.join(store._directory, "index.json"), "w") as handle:
            handle.write("{broken")
        self.assertEqual(store.status("c1"), "none")
        self.assertIsNone(store.active())

    def test_missing_file_means_no_project(self):
        store = WorkspaceStore(tempfile.mkdtemp())
        os.makedirs(store.directory("c1"))
        with open(store.temp_path("c1"), "w") as handle:
            handle.write("x")
        store.commit("c1")
        self.assertEqual(store.status("c1"), "saved")
        os.remove(store.path_for("c1"))
        self.assertEqual(store.status("c1"), "none")


    def test_chats_are_listed_newest_first_with_titles(self):
        store = WorkspaceStore(tempfile.mkdtemp())
        first = store.create("ask")["id"]
        second = store.create("auto")["id"]
        store.save_messages(first, [{"role": "user", "content": "  Шестерня   для  редуктора "}])
        rows = store.chats()
        self.assertEqual(rows[0]["id"], first)
        self.assertEqual(rows[0]["title"], "Шестерня для редуктора")
        self.assertEqual(rows[1]["mode"], "auto")
        self.assertEqual(store.load(second)["messages"], [])

    def test_active_chat_that_was_deleted_is_forgotten(self):
        store = WorkspaceStore(tempfile.mkdtemp())
        store.set_active("gone")
        self.assertIsNone(store.active())


def service_with_chat(port):
    store = WorkspaceStore(tempfile.mkdtemp())
    store.create("ask")
    return WorkspaceService(port, store), store.chats()[0]["id"]


class ServiceTests(unittest.TestCase):
    def test_failed_save_keeps_last_good_copy(self):
        port = WorkspacePort()
        service, c1 = service_with_chat(port)
        port.scene = ["a"]
        service.save(c1)
        port.scene = ["a", "b"]
        port.fail_save = True
        with self.assertRaises(WorkspaceError):
            service.save(c1)
        port.fail_save = False
        port.scene = []
        service.open(c1)
        self.assertEqual(port.scene, ["a"])
        self.assertFalse(os.path.exists(service.store.temp_path(c1)))

    def test_empty_scene_is_saved_as_empty_project(self):
        port = WorkspacePort()
        service, c1 = service_with_chat(port)
        self.assertEqual(service.save(c1), "empty")
        port.scene = ["x"]
        service.open(c1)
        self.assertEqual(port.scene, [])

    def test_corrupt_project_is_reported_not_loaded(self):
        port = WorkspacePort()
        service, c1 = service_with_chat(port)
        port.scene = ["a"]
        service.save(c1)
        with open(service.store.path_for(c1), "wb") as handle:
            handle.write(b"garbage")
        port.scene = ["keep"]
        with self.assertRaises(WorkspaceError):
            service.open(c1)
        self.assertEqual(port.scene, ["keep"])


class SwitchingTests(unittest.TestCase):
    def test_each_chat_gets_its_own_scene_and_new_chat_starts_empty(self):
        presenter, port, _, c1, c2 = two_projects()
        self.assertEqual(port.scene, [])
        port.scene = ["lid"]
        presenter.open_conversation(c1)
        self.assertEqual(port.scene, ["bracket"])
        port.scene = ["bracket", "hand-edit"]
        presenter.open_conversation(c2)
        self.assertEqual(port.scene, ["lid"])
        presenter.open_conversation(c1)
        self.assertEqual(port.scene, ["bracket", "hand-edit"])
        self.assertIsNone(presenter.state.switching)
        self.assertEqual(port.lock_log[-2:], [True, False])

    def test_switching_restores_messages_of_the_chat(self):
        presenter, _, store, c1, c2 = two_projects()
        store.save_messages(c1, [{"role": "user", "content": "первый"}])
        presenter.open_conversation(c1)
        self.assertEqual(presenter.view()["entries"][0]["text"], "первый")
        presenter.open_conversation(c2)
        self.assertEqual(presenter.view()["entries"], [])

    def test_new_project_from_current_scene_keeps_models(self):
        presenter, port, store = build()
        presenter.start()
        presenter.new_conversation()
        first = presenter.state.conversation_id
        port.scene = ["part"]
        presenter.new_conversation(from_scene=True)
        second = presenter.state.conversation_id
        self.assertNotEqual(first, second)
        self.assertEqual(port.scene, ["part"])
        self.assertEqual(store.status(second), "saved")
        self.assertEqual(store.status(first), "saved")

    def test_save_failure_keeps_current_project_and_offers_retry(self):
        presenter, port, _, c1, c2 = two_projects()
        port.scene = ["lid"]
        port.fail_save = True
        presenter.open_conversation(c1)
        self.assertEqual(presenter.state.conversation_id, c2)
        self.assertEqual(port.scene, ["lid"])
        self.assertIn(T["switch_save_failed"], presenter.state.notice)
        self.assertTrue(presenter.state.switch_retry is not None)
        port.fail_save = False
        presenter.retry_switch()
        self.assertEqual(presenter.state.conversation_id, c1)
        self.assertEqual(port.scene, ["bracket"])

    def test_open_failure_restores_previous_project(self):
        presenter, port, store, c1, c2 = two_projects()
        port.scene = ["lid"]
        with open(store.path_for(c1), "wb") as handle:
            handle.write(b"garbage")
        presenter.open_conversation(c1)
        self.assertEqual(presenter.state.conversation_id, c2)
        self.assertEqual(port.scene, ["lid"])
        self.assertIn(T["switch_open_restored"], presenter.state.notice)
        self.assertFalse(presenter.state.workspace_blocked)

    def test_double_failure_blocks_agent_and_recovery_unblocks(self):
        presenter, port, _, c1, _ = two_projects()
        port.scene = ["lid"]
        port.fail_load = True
        presenter.open_conversation(c1)
        self.assertTrue(presenter.state.workspace_blocked)
        self.assertTrue(port.locked)
        presenter.send("hello")
        self.assertEqual(presenter.loop.turns, [])
        port.fail_load = False
        presenter.recover_workspace()
        self.assertFalse(presenter.state.workspace_blocked)
        self.assertFalse(port.locked)
        self.assertEqual(port.scene, ["lid"])

    def test_running_agent_asks_before_switching(self):
        presenter, _, _, c1, c2 = two_projects()
        presenter.send("go")
        presenter.open_conversation(c1)
        self.assertEqual(presenter.state.conversation_id, c2)
        self.assertTrue(presenter.view()["switch_prompt"])
        presenter.cancel_switch()
        self.assertFalse(presenter.view()["switch_prompt"])
        presenter.open_conversation(c1)
        presenter.stop_and_switch()
        self.assertTrue(presenter.loop.turns[0].cancelled)
        self.assertEqual(presenter.state.conversation_id, c1)

    def test_pending_switch_runs_when_the_turn_ends(self):
        presenter, _, _, c1, c2 = two_projects()
        presenter.send("go")
        presenter.open_conversation(c1)
        self.assertTrue(presenter.view()["switch_prompt"])
        presenter.loop.turns[0].emit("finished")
        self.assertFalse(presenter.view()["switch_prompt"])
        self.assertEqual(presenter.state.conversation_id, c1)

    def test_dismissed_switch_stays_on_the_chat(self):
        presenter, _, _, c1, c2 = two_projects()
        presenter.send("go")
        presenter.open_conversation(c1)
        presenter.cancel_switch()
        presenter.loop.turns[0].emit("finished")
        self.assertEqual(presenter.state.conversation_id, c2)

    def test_stop_and_switch_waits_for_a_running_tool(self):
        presenter, _, _, c1, c2 = two_projects()
        presenter.send("go")
        turn = presenter.loop.turns[0]
        turn.release_on_cancel = False
        presenter.open_conversation(c1)
        presenter.stop_and_switch()
        self.assertEqual(presenter.state.conversation_id, c2)
        turn.emit("finished")
        self.assertEqual(presenter.state.conversation_id, c1)

    def test_open_question_does_not_block_switching(self):
        presenter, _, _, c1, _ = two_projects()
        presenter.send("go")
        presenter.loop.turns[0].emit("finished")
        presenter.open_conversation(c1)
        self.assertEqual(presenter.state.conversation_id, c1)

    def test_restart_restores_active_project_and_messages(self):
        presenter, port, store, c1, _ = two_projects()
        store.save_messages(c1, [{"role": "user", "content": "старое"}])
        port.scene = ["lid"]
        presenter.open_conversation(c1)
        fresh = ChatPresenter(presenter._settings, WorkspaceService(port, store), FakeLoop(), FakeLlm(), FakeHub(),
                              ImmediateRunner(), lambda: None)
        port.scene = []
        fresh.start()
        self.assertEqual(fresh.state.conversation_id, c1)
        self.assertEqual(port.scene, ["bracket"])
        self.assertFalse(port.locked)
        self.assertEqual(fresh.view()["entries"][0]["text"], "старое")
        self.assertEqual(len(fresh.state.conversations), 2)


class DraftTests(unittest.TestCase):
    def test_drafts_and_attachments_stay_with_their_chat(self):
        presenter, _, _, c1, c2 = two_projects()
        presenter.set_draft("second chat text")
        presenter.state.attachments.append({"name": "x.stl", "path": "/x.stl", "kind": "model"})
        presenter.open_conversation(c1)
        self.assertEqual(presenter.state.draft, "")
        self.assertEqual(presenter.state.attachments, [])
        presenter.open_conversation(c2)
        self.assertEqual(presenter.state.draft, "second chat text")
        self.assertEqual(presenter.state.attachments[0]["name"], "x.stl")


class ManualTimer(object):
    def __init__(self, delay, callback):
        self.callback = callback
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


class AutosaveTests(unittest.TestCase):
    def test_scene_change_marks_dirty_then_saves_after_delay(self):
        presenter, port, _, _, c2 = two_projects()
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
        presenter._workspace.open(c2)
        self.assertEqual(port.scene, ["lid", "more"])

    def test_failed_autosave_is_reported(self):
        presenter, port, _, _, _ = two_projects()
        port.scene = ["lid"]
        port.fail_save = True
        presenter._autosave.save_now()
        self.assertEqual(presenter.state.save_state, "failed")
        self.assertIn(T["save_failed"], presenter.state.notice)

    def test_changes_during_switch_are_not_autosaved(self):
        presenter, _, _, _, _ = two_projects()
        presenter.state.switching = "opening"
        presenter.state.save_state = "saved"
        presenter.on_scene_changed()
        self.assertEqual(presenter.state.save_state, "saved")

    def test_flush_saves_pending_changes(self):
        presenter, port, store, _, c2 = two_projects()
        port.scene = ["lid"]
        presenter.on_scene_changed()
        presenter.flush_workspace()
        self.assertEqual(presenter.state.save_state, "saved")
        self.assertEqual(store.status(c2), "saved")


if __name__ == "__main__":
    unittest.main()
