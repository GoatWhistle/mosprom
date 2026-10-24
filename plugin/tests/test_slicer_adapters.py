import json
import threading
import unittest
from unittest import mock

from Brim.execution.errors import OperationError, OutcomeUnknown
from Brim.slicer.main_thread import MainThread
from Brim.slicer.port import SlicerPort
from Brim.slicer.settings_ops import SettingsOperations
from Brim.slicer.state import StateReader


class FakeApplication(object):
    def __init__(self, deliver=True):
        self.deliver = deliver
        self.pending = []

    def callLater(self, function, *args):
        if self.deliver:
            threading.Thread(target=function, args=args).start()
        else:
            self.pending.append(function)


class MainThreadTests(unittest.TestCase):
    def test_runs_inline_on_the_owner_thread_and_marshals_from_others(self):
        main = MainThread(FakeApplication())
        self.assertEqual(main.call(lambda value: value + 1, 1), 2)
        seen = {}

        def worker():
            seen["value"] = main.call(lambda: threading.current_thread().name)

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(5)
        self.assertNotEqual(seen["value"], threading.current_thread().name)

    def test_timeout_reports_unknown_outcome(self):
        main = MainThread(FakeApplication(deliver=False))
        result = {}

        def worker():
            try:
                main.call(lambda: None, timeout=0.1)
            except OutcomeUnknown as error:
                result["error"] = error

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(5)
        self.assertEqual(result["error"].code, "outcome_unknown")

    def test_errors_propagate(self):
        main = MainThread(FakeApplication())
        result = {}

        def worker():
            try:
                main.call(lambda: 1 / 0)
            except ZeroDivisionError as error:
                result["error"] = error

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(5)
        self.assertIn("error", result)


def fake_host():
    host = mock.MagicMock()
    stack = mock.MagicMock()
    extruder = mock.MagicMock()
    extruder.isEnabled = True
    extruder.getId.return_value = "ext0"
    extruder.userChanges.getAllKeys.return_value = ["infill_sparse_density"]
    extruder.getProperty.return_value = 20
    stack.extruders = {"0": extruder}
    stack.getId.return_value = "global"
    stack.userChanges.getAllKeys.return_value = ["layer_height"]
    stack.getProperty.side_effect = lambda key, prop: {"layer_height": 0.2, "printing_mode": "classic"}.get(key, 400)
    manager = host.machine_manager.return_value
    manager.activeMachine = stack
    manager.currentRootMaterialId = {"0": "generic_petg"}
    manager.activeVariantNames = {"0": "0.4"}
    manager.activeMachineName = "Hybrid 530"
    manager.activeDefinitionId = "hybrid"
    manager.activeQualityOrQualityChangesName = "Normal"
    manager.activeQualityType = "normal"
    manager.activeQualityLayerHeight = 0.2
    manager.stacksHaveErrors = False
    group = mock.MagicMock(is_available=True)
    host.application.getQualityManager.return_value.getQualityGroups.return_value = {"normal": group}
    host.application.getQualityManager.return_value.getQualityChangesGroups.return_value = {"mine": object()}
    host.global_stack.return_value = stack
    return host, stack


class StateTests(unittest.TestCase):
    def test_state_is_json_serialisable_and_complete(self):
        host, _ = fake_host()
        access = mock.MagicMock()
        access.objects.return_value = []
        state = StateReader(host, access).read()
        json.dumps(state)
        self.assertEqual(state["printer"]["extruders"][0]["material_id"], "generic_petg")
        self.assertEqual(state["mode"], "classic")
        self.assertEqual(state["available_profiles"], ["normal"])
        self.assertEqual(state["custom_profiles"], ["mine"])
        self.assertIn("global:layer_height", state["overrides"])

    def test_failing_catalog_degrades_to_warning(self):
        host, _ = fake_host()
        host.application.getQualityManager.return_value.getQualityGroups.side_effect = RuntimeError("api changed")
        access = mock.MagicMock()
        access.objects.return_value = []
        state = StateReader(host, access).read()
        self.assertTrue([item for item in state["errors"] if "profiles unavailable" in item])

    def test_no_printer(self):
        host, _ = fake_host()
        host.machine_manager.return_value.activeMachine = None
        self.assertIsNone(StateReader(host, mock.MagicMock()).read()["printer"])


class PortWatchTests(unittest.TestCase):
    def test_missing_signals_are_reported_not_fatal(self):
        host, _ = fake_host()
        manager = host.machine_manager.return_value
        del manager.extruderChanged
        port = SlicerPort(host, None, None, mock.MagicMock(), mock.MagicMock(), None, None, None, None, mock.MagicMock())
        self.assertEqual(port.watch(), ["extruderChanged"])

    def test_scene_change_bumps_version_for_sliceable_nodes_only(self):
        host, _ = fake_host()

        class Node(object):
            def __init__(self, sliceable):
                self.sliceable = sliceable

            def callDecoration(self, name):
                return self.sliceable if name == "isSliceable" else False

        host.SceneNode = Node
        host.scene.return_value.getRoot.return_value = object()
        port = SlicerPort(host, None, None, mock.MagicMock(), mock.MagicMock(), None, None, None, None, mock.MagicMock())
        calls = []
        port.add_change_listener(lambda: calls.append(1))
        before = port.scene_version()
        port._on_scene_changed(Node(False))
        self.assertEqual(port.scene_version(), before)
        port._on_scene_changed(Node(True))
        self.assertEqual(port.scene_version(), before + 1)
        self.assertEqual(calls, [1])


class SettingsOperationTests(unittest.TestCase):
    def make(self):
        host, stack = fake_host()

        class Main(object):
            def call(self, function, *args, guard=None):
                if guard:
                    guard()
                return function(*args)

        return SettingsOperations(host, Main()), host, stack

    def test_mode_must_be_offered(self):
        ops, host, stack = self.make()
        stack.getSettingDefinition.return_value = mock.MagicMock(options={"classic": "3D", "cylindrical": "5D"})
        self.assertEqual(ops.select_mode({"mode": "cylindrical"}), {"mode": "cylindrical"})
        stack.userChanges.setProperty.assert_called_with("printing_mode", "value", "cylindrical")
        with self.assertRaises(OperationError):
            ops.select_mode({"mode": "cylindrical_full"})

    def test_unknown_setting_and_mode_key_are_rejected(self):
        ops, host, stack = self.make()
        stack.getSettingDefinition.return_value = None
        with self.assertRaises(OperationError):
            ops.set_global({"key": "nope", "value": 1})
        stack.getSettingDefinition.return_value = mock.MagicMock()
        with self.assertRaises(OperationError):
            ops.set_global({"key": "printing_mode", "value": "classic"})

    def test_extruder_setting_targets_extruder_stack(self):
        ops, host, stack = self.make()
        stack.getSettingDefinition.return_value = mock.MagicMock()
        ops.set_extruder({"key": "infill_sparse_density", "value": 30, "extruder": 0})
        stack.extruders["0"].userChanges.setProperty.assert_called_with("infill_sparse_density", "value", 30)
        with self.assertRaises(OperationError):
            ops.set_extruder({"key": "infill_sparse_density", "value": 30, "extruder": 3})

    def test_unknown_profile_lists_choices(self):
        ops, host, stack = self.make()
        with self.assertRaises(OperationError) as caught:
            ops.select_profile({"profile_id": "ultra"})
        self.assertEqual(caught.exception.details["quality_types"], ["normal"])


if __name__ == "__main__":
    unittest.main()
