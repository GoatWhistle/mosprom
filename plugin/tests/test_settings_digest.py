import json
from collections import OrderedDict
import unittest
from unittest import mock

from Brim.slicer.port import SlicerPort
from Brim.slicer.settings_digest import SettingsDigest


class Definition(object):
    def __init__(self, key, type_="float", unit="", children=None, options=None, per_extruder=False):
        self.key = key
        self.type = type_
        self.unit = unit
        self.children = children or []
        self.options = options
        self.settable_per_extruder = per_extruder


class Stack(object):
    def __init__(self, values, user_keys=()):
        self.values = values
        self.userChanges = mock.Mock()
        self.userChanges.getAllKeys.return_value = list(user_keys)
        self.isEnabled = True

    def getProperty(self, key, name):
        return self.values.get((key, name))


def make_host(extruder_values=None):
    values = {
        ("speed_infill", "enabled"): True, ("speed_infill", "value"): 60.000000001,
        ("speed_infill", "minimum_value"): 0.1, ("speed_infill_cylindrical", "enabled"): True,
        ("speed_infill_cylindrical", "value"): 40, ("support_enable", "enabled"): True,
        ("support_enable", "value"): False, ("support_pattern", "enabled"): False,
        ("support_type", "enabled"): True, ("support_type", "value"): "buildplate",
        ("machine_width", "enabled"): True, ("machine_width", "value"): 300,
    }
    stack = Stack(values, ["speed_infill"])
    stack.extruders = {"0": Stack({}), "1": Stack(extruder_values or {})}
    stack.extruders["0"].values = dict((key, value) for key, value in values.items())
    speed = Definition("speed", "category", children=[
        Definition("speed_infill", unit="mm/s", per_extruder=True,
                   children=[Definition("speed_infill_cylindrical", unit="mm/s")]),
    ])
    support = Definition("support", "category", children=[
        Definition("support_enable", "bool", children=[Definition("support_pattern", "enum")]),
        Definition("support_type", "enum", options=OrderedDict([("buildplate", "Touching Buildplate"), ("everywhere", "Everywhere")])),
    ])
    machine = Definition("machine_settings", "category", children=[Definition("machine_width", unit="mm")])
    stack.definition = mock.Mock(definitions=[machine, speed, support])
    host = mock.Mock()
    host.global_stack.return_value = stack
    return host


class SettingsDigestTests(unittest.TestCase):
    def test_lists_enabled_settings_by_category_in_tree_order(self):
        digest = SettingsDigest(make_host({("speed_infill", "value"): 30})).read()
        json.dumps(digest)
        self.assertEqual([group["category"] for group in digest], ["speed", "support"])
        self.assertEqual(digest[0]["settings"], [
            "*speed_infill = 60.0 mm/s (float; 0.1..; e0=60.0, e1=30)",
            "speed_infill_cylindrical = 40 mm/s (float)",
        ])
        self.assertEqual(digest[1]["settings"], [
            "support_enable = false (bool)",
            "support_type = buildplate (enum; buildplate|everywhere)",
        ])

    def test_equal_extruder_values_are_not_repeated(self):
        digest = SettingsDigest(make_host({("speed_infill", "value"): 60.0})).read()
        self.assertEqual(digest[0]["settings"][0], "*speed_infill = 60.0 mm/s (float; 0.1..)")

    def test_result_is_cached_until_invalidated(self):
        host = make_host()
        digest = SettingsDigest(host)
        first = digest.read()
        host.global_stack.return_value.values[("support_enable", "value")] = True
        self.assertIs(digest.read(), first)
        digest.invalidate()
        self.assertIn("support_enable = true (bool)", digest.read()[1]["settings"])

    def test_no_printer_gives_empty_digest(self):
        host = mock.Mock()
        host.global_stack.return_value = None
        self.assertEqual(SettingsDigest(host).read(), [])


class SnapshotSettingsTests(unittest.TestCase):
    def make_port(self, digest):
        main = mock.Mock()
        main.call.side_effect = lambda function, *args, **kwargs: function(*args)
        state = mock.Mock()
        state.read.side_effect = lambda: {"errors": []}
        return SlicerPort(mock.Mock(), None, state, mock.Mock(), mock.Mock(), None, None, None, main, digest), state

    def test_snapshot_carries_settings_but_tool_state_does_not(self):
        digest = mock.Mock()
        digest.read.return_value = [{"category": "speed", "settings": ["a = 1 (int)"]}]
        port, _ = self.make_port(digest)
        self.assertEqual(port.snapshot()[1]["settings"], digest.read.return_value)
        self.assertNotIn("settings", port.read_state())

    def test_digest_failure_degrades_to_error(self):
        digest = mock.Mock()
        digest.read.side_effect = RuntimeError("api changed")
        port, _ = self.make_port(digest)
        state = port.snapshot()[1]
        self.assertNotIn("settings", state)
        self.assertEqual(state["errors"], ["settings unavailable: api changed"])

    def test_settings_signals_and_operations_invalidate_the_digest(self):
        digest = mock.Mock()
        port, _ = self.make_port(digest)
        port._settings_changed()
        port._handlers["arrange"] = mock.Mock(side_effect=RuntimeError("boom"))
        with self.assertRaises(RuntimeError):
            port.apply_operation({"kind": "arrange"})
        self.assertEqual(digest.invalidate.call_count, 2)


if __name__ == "__main__":
    unittest.main()
