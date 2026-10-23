import json
import threading
import unittest

from tests.agent_harness import Harness, call_reply, calls_reply, done_reply
from tests.scripted_llm import text_reply
from Brim.agent.transcript import pending_question


def payload(message):
    return json.loads(message["content"])


BED_40_TO = lambda value: {"operations": [{"kind": "set_global_setting", "key": "material_bed_temperature", "value": value}]}


class FullScenarioTests(unittest.TestCase):
    def test_question_answer_settings_change_and_slice(self):
        harness = Harness([
            call_reply("q1", "ask_user", {"questions": [{"text": "Материал?", "options": ["PLA", "PETG"]}]}),
            call_reply("s1", "search_settings", {"query": "bed"}),
            call_reply("a1", "apply_changes", BED_40_TO(60)),
            call_reply("sl", "slice", {}),
            done_reply("G-code готов"),
        ])
        self.addCleanup(harness.stop)
        harness.run(text="Кронштейн")
        self.assertIn("question", harness.kinds())
        self.assertEqual(pending_question(harness.conversation.messages())["questions"][0]["options"], ["PLA", "PETG"])
        self.assertEqual(len(harness.llm_server.requests), 1)

        harness.run(answer="PETG")
        tools = harness.tool_messages()
        self.assertEqual([item["tool_call_id"] for item in tools], ["q1", "s1", "a1", "sl"])
        self.assertEqual(payload(tools[0]), {"answer": "PETG"})
        self.assertEqual([item["brim_status"] for item in tools], ["ok", "ok", "ok", "ok"])
        self.assertIn("confirm", harness.kinds())
        self.assertEqual(harness.port.applied[0]["value"], 60)
        files = payload(tools[3])["result"]["files"]
        self.assertTrue(files["gcode"].startswith(harness.directory))
        self.assertEqual(harness.conversation.messages()[-1]["content"], "G-code готов")
        self.assertTrue(harness.saved)

    def test_requests_are_valid_openai_messages(self):
        harness = Harness([call_reply("s1", "inspect_profile", {}), done_reply()])
        self.addCleanup(harness.stop)
        harness.run(text="hi")
        second = harness.llm_server.requests[1]
        self.assertEqual(second["model"], "scripted")
        self.assertEqual(second["messages"][0]["role"], "system")
        self.assertIn("material_bed_temperature = 40", second["messages"][0]["content"])
        roles = [item["role"] for item in second["messages"]]
        self.assertEqual(roles, ["system", "user", "assistant", "tool"])
        self.assertFalse([key for item in second["messages"] for key in item if key.startswith("brim_")])
        names = [tool["function"]["name"] for tool in second["tools"]]
        self.assertIn("ask_user", names)
        self.assertIn("apply_changes", names)


class ConfirmationTests(unittest.TestCase):
    def test_rejection_returns_the_comment_to_the_model(self):
        harness = Harness([call_reply("a1", "apply_changes", BED_40_TO(60)), done_reply()])
        self.addCleanup(harness.stop)
        harness.decisions.append(("reject", "оставь 40"))
        harness.run(text="go")
        result = harness.tool_messages()[0]
        self.assertEqual(result["brim_status"], "rejected")
        self.assertIn("оставь 40", payload(result)["error"]["message"])
        self.assertEqual(harness.port.applied, [])
        self.assertIn("оставь 40", json.dumps(harness.llm_server.requests[1]["messages"][-1], ensure_ascii=False))

    def test_auto_mode_applies_safe_change_without_card(self):
        harness = Harness([call_reply("a1", "apply_changes", BED_40_TO(60)), done_reply()], mode="auto")
        self.addCleanup(harness.stop)
        harness.run(text="go")
        self.assertNotIn("confirm", harness.kinds())
        self.assertEqual(harness.port.applied[0]["value"], 60)

    def test_auto_mode_still_confirms_risky_change(self):
        harness = Harness([call_reply("a1", "apply_changes", BED_40_TO(500)), done_reply()], mode="auto")
        self.addCleanup(harness.stop)
        harness.decisions.append(("reject", ""))
        harness.run(text="go")
        card = [item for kind, item in harness.events if kind == "confirm"][0]
        self.assertEqual(card["items"][0]["reason"], "out_of_range")
        self.assertEqual(card["items"][0]["limits"], "0..120")
        self.assertEqual(card["items"][0]["detail"], "40 → 500 °C")
        self.assertEqual(harness.port.applied, [])

    def test_auto_mode_slice_runs_without_card(self):
        harness = Harness([call_reply("sl", "slice", {}), done_reply()], mode="auto")
        self.addCleanup(harness.stop)
        harness.run(text="go")
        self.assertNotIn("confirm", harness.kinds())
        self.assertEqual(harness.port.slices, 1)


class RecoveryTests(unittest.TestCase):
    def test_open_question_survives_restart(self):
        harness = Harness([call_reply("q1", "ask_user", {"questions": [{"text": "Нагрузка?"}]}),
                           call_reply("p1", "inspect_profile", {}), done_reply("ok")])
        self.addCleanup(harness.stop)
        harness.run(text="деталь")
        restored = harness.new_conversation(harness.saved[-1])
        self.assertEqual(pending_question(restored.messages())["call_id"], "q1")
        harness.conversation = restored
        harness.run(answer="10 кг")
        tools = harness.tool_messages()
        self.assertEqual(payload(tools[0]), {"answer": "10 кг"})
        self.assertEqual(tools[1]["tool_call_id"], "p1")

    def test_new_message_instead_of_answer_closes_question(self):
        harness = Harness([call_reply("q1", "ask_user", {"questions": [{"text": "?"}]}), done_reply()])
        self.addCleanup(harness.stop)
        harness.run(text="a")
        harness.run(text="другая тема")
        self.assertEqual(payload(harness.tool_messages()[0])["error"]["code"], "not_answered")
        self.assertIsNone(pending_question(harness.conversation.messages()))

    def test_step_limit_stops_the_turn(self):
        harness = Harness([call_reply("p%d" % index, "inspect_profile", {}) for index in range(5)], max_steps=3)
        self.addCleanup(harness.stop)
        harness.run(text="loop")
        errors = [item for kind, item in harness.events if kind == "error"]
        self.assertEqual(errors[0]["code"], "step_limit")
        self.assertEqual(len(harness.llm_server.requests), 3)

    def test_llm_error_is_reported(self):
        harness = Harness([])
        harness.llm_server.stop()
        harness.run(text="hi")
        errors = [item for kind, item in harness.events if kind == "error"]
        self.assertEqual(errors[0]["code"], "llm")

    def test_cancel_while_waiting_for_model_discards_its_reply(self):
        gate = threading.Event()

        def slow():
            gate.wait(5)
            return call_reply("a1", "apply_changes", BED_40_TO(60))

        harness = Harness([slow])
        self.addCleanup(harness.stop)
        turn = harness.loop.turn(harness.conversation, lambda: "auto", harness.emit)
        turn.start(text="go")
        while not harness.llm_server.requests:
            gate.wait(0.01)
        self.assertTrue(turn.cancel())
        gate.set()
        turn.join(5)
        self.assertEqual(harness.port.applied, [])
        self.assertEqual([item["role"] for item in harness.conversation.messages()], ["user"])

    def test_invalid_tool_arguments_are_reported_to_the_model(self):
        broken = {"choices": [{"message": {"role": "assistant", "content": None, "tool_calls": [
            {"id": "x", "type": "function", "function": {"name": "slice", "arguments": "{oops"}}]}}]}
        harness = Harness([broken, done_reply()])
        self.addCleanup(harness.stop)
        harness.run(text="go")
        self.assertEqual(payload(harness.tool_messages()[0])["error"]["code"], "invalid_arguments")
        self.assertEqual(harness.port.slices, 0)

    def test_render_image_is_sent_after_tool_results(self):
        harness = Harness([calls_reply(("r1", "render_scene", {"view": "iso"}), ("p1", "inspect_profile", {})),
                           done_reply()])
        self.addCleanup(harness.stop)
        harness.run(text="look")
        messages = harness.llm_server.requests[1]["messages"]
        self.assertEqual([item["role"] for item in messages[-3:]], ["tool", "tool", "user"])
        self.assertTrue(messages[-1]["content"][1]["image_url"]["url"].startswith("data:image/png;base64,"))

    def test_model_reply_without_tools_ends_turn(self):
        harness = Harness([text_reply("Привет")])
        self.addCleanup(harness.stop)
        harness.run(text="hi")
        self.assertEqual(harness.conversation.messages()[-1], {"role": "assistant", "content": "Привет"})


if __name__ == "__main__":
    unittest.main()
