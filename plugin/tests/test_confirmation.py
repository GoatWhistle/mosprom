import unittest

from tests import support
from Brim.agent.confirmation import ConfirmationPolicy

BRIM = {"server": "brim", "tool": "apply_changes", "name": "apply_changes", "annotations": {}}


def bed(value):
    return {"operations": [{"kind": "set_global_setting", "key": "material_bed_temperature", "value": value},
                           {"kind": "arrange"}]}


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.port = support.FakePort()
        self.policy = ConfirmationPolicy(self.port.setting_facts, "2")

    def review(self, mode, arguments, tool=BRIM):
        return self.policy.review(mode, tool, arguments)

    def test_ask_mode_confirms_every_change_and_slice(self):
        items = self.review("ask", bed(60))
        self.assertEqual([item["kind"] for item in items], ["set_global_setting", "arrange"])
        self.assertFalse(items[0]["risky"])
        slice_tool = dict(BRIM, tool="slice", name="slice")
        self.assertEqual(self.review("ask", {}, slice_tool)[0]["kind"], "slice")
        self.assertIsNone(self.review("auto", {}, slice_tool))
        self.assertIsNone(self.review("ask", {}, dict(BRIM, tool="inspect_profile")))

    def test_auto_mode_flags_ranges_and_large_changes(self):
        self.assertIsNone(self.review("auto", bed(60)))
        self.assertEqual(self.review("auto", bed(500))[0]["reason"], "out_of_range")
        self.assertEqual(self.review("auto", bed(115))[0]["reason"], "out_of_recommended")
        self.assertEqual(self.review("auto", bed(15))[0]["reason"], "out_of_recommended")
        self.port.facts["material_bed_temperature"]["minimum_value_warning"] = None
        self.assertEqual(self.review("auto", bed(15))[0]["reason"], "large_change")
        self.assertIsNone(self.review("auto", bed(80)))
        self.assertEqual(len(self.review("auto", bed(500))), 1)

    def test_unknown_setting_or_expression_is_not_risky(self):
        operations = {"operations": [{"kind": "set_global_setting", "key": "unknown", "value": 5},
                                     {"kind": "set_global_setting", "key": "material_bed_temperature", "value": "=x"}]}
        self.assertIsNone(self.review("auto", operations))

    def test_external_tools_follow_annotations(self):
        read_only = {"server": "ext", "name": "ext__get", "tool": "get", "annotations": {"readOnlyHint": True}}
        plain = {"server": "ext", "name": "ext__put", "tool": "put", "annotations": {}}
        destructive = {"server": "ext", "name": "ext__rm", "tool": "rm", "annotations": {"destructiveHint": True}}
        self.assertIsNone(self.review("ask", {}, read_only))
        self.assertEqual(self.review("ask", {"a": 1}, plain)[0]["detail"], '{"a": 1}')
        self.assertIsNone(self.review("auto", {}, plain))
        self.assertTrue(self.review("auto", {}, destructive)[0]["risky"])

    def test_bad_ratio_falls_back_to_default(self):
        self.assertEqual(ConfirmationPolicy(self.port.setting_facts, "abc").ratio(), 2.0)
        self.assertEqual(ConfirmationPolicy(self.port.setting_facts, lambda: "3").ratio(), 3.0)


if __name__ == "__main__":
    unittest.main()
