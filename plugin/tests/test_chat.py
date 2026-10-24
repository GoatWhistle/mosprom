import json
import os
import tempfile
import unittest

from tests.chat_fakes import build, make_settings, two_projects
from Brim.chat.entries_view import agent_status, build_entries, group_entries
from Brim.chat.view import chat_view
from Brim.ui.strings import STRINGS

T = STRINGS["ru"]


def assistant_calls(*calls):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}
        for call_id, name, arguments in calls]}


def tool_result(call_id, name, payload, status="ok", server="brim"):
    return {"role": "tool", "tool_call_id": call_id, "content": json.dumps(payload), "brim_tool": name,
            "brim_status": status, "brim_server": server}


class SendTests(unittest.TestCase):
    def test_first_message_creates_chat_bound_to_current_scene(self):
        presenter, port, store = build()
        presenter.start()
        port.scene = ["part"]
        presenter.send("Кронштейн")
        conversation_id = presenter.state.conversation_id
        self.assertIsNotNone(conversation_id)
        self.assertEqual(store.status(conversation_id), "saved")
        self.assertEqual(store.active(), conversation_id)
        turn = presenter.loop.turns[0]
        self.assertEqual(turn.started["text"], "Кронштейн")
        self.assertTrue(presenter.state.running)
        self.assertEqual(presenter.state.draft, "")

    def test_send_requires_llm_settings(self):
        presenter, _, _ = build(settings=make_settings(llm_base_url="", llm_model=""))
        presenter.start()
        presenter.send("hi")
        self.assertEqual(presenter.loop.turns, [])
        self.assertEqual(presenter.state.notice, T["llm_missing"])

    def test_send_is_blocked_while_turn_runs(self):
        presenter, _, _, _, _ = two_projects()
        presenter.send("a")
        presenter.send("b")
        self.assertEqual(len(presenter.loop.turns), 1)
        self.assertEqual(presenter.state.notice, T["busy_run"])

    def test_text_after_question_is_an_answer(self):
        presenter, _, _, _, _ = two_projects()
        presenter.send("start")
        turn = presenter.loop.turns[0]
        turn.conversation.append(assistant_calls(("q1", "ask_user", {"questions": [{"text": "?"}]})))
        turn.emit("question")
        turn.emit("finished")
        self.assertFalse(presenter.state.running)
        view = presenter.view()
        self.assertEqual(view["question"]["call_id"], "q1")
        self.assertEqual(view["status_text"], T["state_awaiting_user"])
        presenter.send("PETG")
        self.assertEqual(presenter.loop.turns[1].started, {"text": None, "attachments": [], "answer": "PETG"})

    def test_attachments_are_copied_into_the_chat_folder(self):
        presenter, _, store, _, chat = two_projects()
        source = os.path.join(tempfile.mkdtemp(), "part.stl")
        with open(source, "wb") as handle:
            handle.write(b"solid")
        presenter.attach(source)
        presenter.attach("/tmp/readme.txt")
        self.assertIn("readme.txt", presenter.state.notice)
        presenter.send("")
        attached = presenter.loop.turns[0].started["attachments"]
        self.assertEqual(len(attached), 1)
        self.assertTrue(attached[0]["path"].startswith(store.files_dir(chat)))
        self.assertEqual(presenter.state.attachments, [])

    def test_confirmation_flow(self):
        presenter, _, _, _, _ = two_projects()
        presenter.send("go")
        turn = presenter.loop.turns[0]
        turn.conversation.append(assistant_calls(("a1", "apply_changes", {"operations": [], "explanation": "Стол"})))
        turn.emit("confirm", {"call_id": "a1", "tool": "apply_changes", "server": "brim", "items": []})
        view = presenter.view()
        self.assertEqual(view["confirmation"]["explanation"], "Стол")
        self.assertEqual(view["entries"][-1]["kind"], "confirmation")
        presenter.send("text while confirming")
        self.assertEqual(presenter.state.notice, T["confirm_first"])
        presenter.confirm("reject", "не надо")
        self.assertEqual(turn.decisions, [("reject", "не надо")])
        self.assertIsNone(presenter.state.confirmation)

    def test_stop_releases_turn_immediately_when_possible(self):
        presenter, _, _, _, _ = two_projects()
        presenter.send("go")
        presenter.stop()
        self.assertTrue(presenter.loop.turns[0].cancelled)
        self.assertFalse(presenter.state.running)

    def test_stop_waits_for_running_tool(self):
        presenter, _, _, _, _ = two_projects()
        presenter.send("go")
        turn = presenter.loop.turns[0]
        turn.release_on_cancel = False
        presenter.stop()
        self.assertTrue(presenter.state.running)
        self.assertEqual(presenter.view()["status_text"], T["state_stopping"])
        turn.emit("finished")
        self.assertFalse(presenter.state.running)

    def test_events_of_a_released_turn_are_ignored(self):
        presenter, _, _, _, _ = two_projects()
        presenter.send("go")
        turn = presenter.loop.turns[0]
        presenter.stop()
        turn.emit("error", {"message": "late"})
        self.assertEqual(presenter.state.errors, [])

    def test_error_event_is_shown(self):
        presenter, _, _, _, _ = two_projects()
        presenter.send("go")
        presenter.loop.turns[0].emit("error", {"message": "LLM returned HTTP 500"})
        presenter.loop.turns[0].emit("finished")
        view = presenter.view()
        self.assertEqual(view["entries"][-1]["kind"], "error")
        self.assertEqual(view["status_kind"], "error")

    def test_mode_is_stored_per_chat(self):
        presenter, _, store, first, second = two_projects()
        presenter.set_mode("auto")
        self.assertEqual(store.load(second)["mode"], "auto")
        presenter.open_conversation(first)
        self.assertEqual(presenter.state.mode, "ask")
        presenter.open_conversation(second)
        self.assertEqual(presenter.state.mode, "auto")

    def test_messages_persist_and_title_comes_from_first_message(self):
        presenter, _, store, _, chat = two_projects()
        presenter.send("Кронштейн для полки")
        turn = presenter.loop.turns[0]
        turn.conversation.save()
        self.assertEqual(store.load(chat)["title"], "Кронштейн для полки")
        self.assertEqual(presenter.state.conversations[0]["title"], "Кронштейн для полки")

    def test_open_folder_opens_chat_output(self):
        presenter, _, store, _, chat = two_projects()
        presenter.open_folder()
        self.assertEqual(presenter.opened, [store.output_dir(chat)])


class SettingsTests(unittest.TestCase):
    def test_view_never_exposes_the_api_key(self):
        presenter, _, _ = build()
        presenter.start()
        self.assertNotIn('"k"', json.dumps(presenter.view()["settings"]))
        self.assertTrue(presenter.view()["settings"]["llm_key_saved"])

    def test_servers_are_added_toggled_and_removed(self):
        presenter, _, _ = build()
        presenter.start()
        self.assertFalse(presenter.add_server("brim", "http://x/mcp", ""))
        self.assertFalse(presenter.add_server("ext", "ftp://x", ""))
        self.assertFalse(presenter.add_server("ext", "http://x/mcp", "no colon"))
        self.assertTrue(presenter.add_server("ext", "http://x/mcp", "Authorization: Bearer t"))
        servers = presenter.view()["servers"]
        self.assertEqual([item["name"] for item in servers], ["brim", "ext"])
        self.assertTrue(servers[0]["pinned"])
        self.assertEqual(presenter._settings.mcp_servers()[0]["headers"], {"Authorization": "Bearer t"})
        presenter.toggle_server("ext", False)
        self.assertEqual(presenter.view()["servers"][1]["state"], "off")
        presenter.remove_server("ext")
        self.assertEqual(len(presenter.view()["servers"]), 1)

    def test_llm_url_is_validated_and_key_kept(self):
        settings = make_settings()
        presenter, _, _ = build(settings=settings)
        self.assertFalse(presenter.apply_settings("ftp://x", "m", "", "ru", "dark"))
        self.assertTrue(presenter.apply_settings("http://h:8000/v1/", "sonnet", "", "en", "light"))
        self.assertEqual(settings.llm(), {"base_url": "http://h:8000/v1", "model": "sonnet", "api_key": "k"})
        self.assertEqual(settings.language(), "en")

    def test_interface_applies_without_touching_llm(self):
        settings = make_settings()
        presenter, _, _ = build(settings=settings)
        before = settings.llm()
        presenter.set_interface("en", "light")
        self.assertEqual((settings.language(), settings.theme()), ("en", "light"))
        self.assertEqual(presenter.view()["theme"], "light")
        self.assertEqual(settings.llm(), before)

    def test_check_reports_models(self):
        presenter, _, _ = build()
        presenter.check_connection()
        self.assertIn(T["check_ok"], presenter.view()["settings_notice"])

    def test_dictionaries_have_the_same_keys(self):
        self.assertEqual(set(STRINGS["ru"]), set(STRINGS["en"]))


class EntryTests(unittest.TestCase):
    def test_tools_questions_and_result_are_rendered(self):
        files = {"gcode": "/c/output/result.gcode", "3mf": "/c/output/result.3mf"}
        messages = [
            {"role": "user", "content": "hi", "brim_attachments": [{"name": "a.stl"}]},
            assistant_calls(("q", "ask_user", {"questions": [{"text": "?", "options": ["A"]}]})),
            tool_result("q", "ask_user", {"answer": "A"}),
            assistant_calls(("a", "apply_changes", {}), ("s", "slice", {}), ("x", "ext__run", {})),
            tool_result("a", "apply_changes", {"ok": True, "applied": [{"kind": "arrange"}]}),
            tool_result("s", "slice", {"ok": True, "result": {"slice": {"print_time_seconds": 60}, "files": files}}),
            tool_result("x", "ext__run", {"ok": False, "error": {"code": "rejected_by_user", "message": "no"}},
                        status="rejected", server="ext"),
            {"role": "user", "content": "img", "brim_hidden": True},
        ]
        entries = build_entries(messages, running=False)
        self.assertEqual([item["kind"] for item in entries], ["user", "question", "tool", "tool", "result", "tool"])
        self.assertEqual(entries[0]["attachments"], ["a.stl"])
        self.assertEqual(entries[1]["answer"], "A")
        self.assertEqual(entries[2]["detail"], "arrange")
        self.assertEqual(entries[4]["result"]["folder"], "/c/output")
        self.assertEqual(entries[5]["tool"], "run")
        self.assertEqual(entries[5]["server"], "ext")
        self.assertEqual(entries[5]["status"], "rejected")

    def test_unanswered_call_is_pending_or_skipped(self):
        messages = [assistant_calls(("a", "inspect_profile", {}))]
        self.assertEqual(build_entries(messages, running=True)[0]["status"], "pending")
        self.assertEqual(build_entries(messages, running=False)[0]["status"], "skipped")

    def test_interrupted_running_call_is_failed_after_restart(self):
        messages = [assistant_calls(("a", "slice", {})),
                    tool_result("a", "slice", {"ok": False, "error": {"code": "interrupted", "message": "x"}}, "running")]
        self.assertEqual(build_entries(messages, running=False)[0]["status"], "failed")

    def test_completed_tools_are_grouped_but_failures_stay_visible(self):
        entries = [{"kind": "tool", "status": "ok", "key": "k1"}, {"kind": "tool", "status": "ok", "key": "k2"},
                   {"kind": "tool", "status": "failed", "key": "k3"}, {"kind": "tool", "status": "ok", "key": "k4"}]
        grouped = group_entries(entries)
        self.assertEqual([item["kind"] for item in grouped], ["tool_group", "tool", "tool"])

    def test_status_priorities(self):
        base = {"switching": None, "workspace_blocked": False, "running": True, "stopping": False,
                "confirmation": None, "question": None, "errors": [],
                "entries": [{"kind": "tool", "tool": "slice", "status": "running"}]}
        self.assertEqual(agent_status(base, T, True)[1], T["tool_active_slice"])
        self.assertEqual(agent_status(dict(base, switching="saving"), T, True)[1], T["status_saving_project"])
        self.assertEqual(agent_status(dict(base, confirmation={}), T, True)[0], "attention")
        self.assertEqual(agent_status(dict(base, running=False, entries=[]), T, False)[1], T["llm_missing"])

    def test_view_is_json_serialisable(self):
        presenter, _, _, _, _ = two_projects()
        json.dumps(chat_view(presenter.state, presenter._settings, 1234, None))


if __name__ == "__main__":
    unittest.main()
