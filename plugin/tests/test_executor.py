import os
import tempfile
import unittest

from tests import support
from Brim.execution.executor import ToolExecutor
from Brim.execution.geometry import analyze


def build():
    directory = tempfile.mkdtemp()
    port = support.FakePort()
    return ToolExecutor(port, lambda: directory), port, directory


class ExecutorTests(unittest.TestCase):
    def test_apply_changes_runs_in_order_and_restores_autoslicing(self):
        executor, port, _ = build()
        ops = [{"kind": "select_mode", "mode": "classic"}, {"kind": "arrange"}]
        reply = executor.execute("apply_changes", {"operations": ops})
        self.assertTrue(reply["ok"])
        self.assertEqual([item["kind"] for item in port.applied], ["select_mode", "arrange"])
        self.assertEqual([item["kind"] for item in reply["applied"]], ["select_mode", "arrange"])
        self.assertEqual(port.batches, 0)

    def test_partial_batch_reports_applied_and_stops(self):
        executor, port, _ = build()
        port.fail_on = "arrange"
        ops = [{"kind": "select_mode", "mode": "classic"}, {"kind": "arrange"}, {"kind": "select_mode", "mode": "cylindrical"}]
        reply = executor.execute("apply_changes", {"operations": ops})
        self.assertFalse(reply["ok"])
        self.assertEqual(len(reply["applied"]), 1)
        self.assertEqual(reply["result"]["failed_index"], 1)
        self.assertEqual(len(port.applied), 1)
        self.assertEqual(port.batches, 0)

    def test_invalid_arguments_are_rejected_before_any_change(self):
        executor, port, _ = build()
        reply = executor.execute("apply_changes", {"operations": [{"kind": "select_mode", "mode": "x"}]})
        self.assertEqual(reply["error"]["code"], "invalid_arguments")
        self.assertEqual(port.applied, [])

    def test_cancel_during_batch_stops_remaining_operations(self):
        executor, port, _ = build()
        original = port.apply_operation

        def apply_and_cancel(op, check=None):
            result = original(op, check)
            executor.cancel()
            return result

        port.apply_operation = apply_and_cancel
        reply = executor.execute("apply_changes", {"operations": [{"kind": "arrange"}, {"kind": "arrange"}]})
        self.assertEqual(reply["error"]["code"], "cancelled")
        self.assertEqual(len(port.applied), 1)
        self.assertEqual(port.cancelled, 1)

    def test_cancel_flag_is_reset_for_the_next_call(self):
        executor, port, _ = build()
        executor.cancel()
        self.assertTrue(executor.execute("apply_changes", {"operations": [{"kind": "arrange"}]})["ok"])

    def test_unknown_tool(self):
        executor, _, _ = build()
        self.assertEqual(executor.execute("ask_user", {})["error"]["code"], "unknown_tool")

    def test_read_tools(self):
        executor, port, _ = build()
        self.assertEqual(executor.execute("search_settings", {"query": "wall"})["result"]["matches"][0]["query"], "wall")
        self.assertEqual(executor.execute("inspect_profile", {})["result"], {"profile": "fine"})
        self.assertFalse(executor.execute("search_settings", {"query": " "})["ok"])
        self.assertEqual(executor.execute("inspect_scene", {})["result"]["state"], port.state)

    def test_render_returns_image_separately(self):
        executor, _, _ = build()
        reply = executor.execute("render_scene", {})
        self.assertEqual(reply["result"], {"view": "iso"})
        self.assertEqual(reply["images"], [{"mime_type": "image/png", "data": b"\x89PNG-fake"}])

    def test_analyze_geometry_cube(self):
        executor, _, _ = build()
        reply = executor.execute("analyze_geometry", {"object_ids": ["obj-1"], "direction": [0, 0, 1]})
        info = reply["result"]["objects"]["obj-1"]
        self.assertTrue(info["closed"])
        self.assertAlmostEqual(info["volume_mm3"], 1000.0, places=3)
        self.assertAlmostEqual(info["surface_area_mm2"], 600.0, places=3)
        self.assertEqual(info["connected_components"], 1)
        self.assertEqual(info["bed_contact_area_mm2"], 100.0)
        self.assertFalse(executor.execute("analyze_geometry", {"object_ids": ["nope"]})["ok"])
        self.assertFalse(executor.execute("analyze_geometry", {"object_ids": ["obj-1"], "direction": [0, 0, 0]})["ok"])

    def test_open_mesh_has_no_volume(self):
        mesh = support.cube_mesh()
        mesh["triangles"] = mesh["triangles"][:-1]
        info = analyze(mesh)
        self.assertFalse(info["closed"])
        self.assertIsNone(info["volume_mm3"])

    def test_slice_writes_both_files_into_the_chat_folder(self):
        executor, port, directory = build()
        reply = executor.execute("slice", {})
        self.assertTrue(reply["ok"])
        self.assertEqual(reply["result"]["slice"]["print_time_seconds"], 600)
        self.assertEqual(sorted(reply["result"]["files"]), ["3mf", "gcode"])
        for path in reply["result"]["files"].values():
            self.assertEqual(os.path.dirname(path), directory)
            self.assertTrue(os.path.isfile(path))

    def test_slice_discards_result_when_scene_changes(self):
        executor, port, _ = build()
        port.bump_on_slice = True
        reply = executor.execute("slice", {})
        self.assertEqual(reply["error"]["code"], "stale_result")
        self.assertEqual(port.exports, 0)

    def test_cancel_during_slice_prevents_export(self):
        executor, port, _ = build()
        original = port.slice

        def slice_and_cancel(report, check=None):
            summary = original(report, check)
            executor.cancel()
            return summary

        port.slice = slice_and_cancel
        reply = executor.execute("slice", {})
        self.assertEqual(reply["error"]["code"], "cancelled")
        self.assertEqual(port.exports, 0)

    def test_slice_without_open_chat_is_refused(self):
        port = support.FakePort()
        reply = ToolExecutor(port, lambda: None).execute("slice", {})
        self.assertEqual(reply["error"]["code"], "not_available")
        self.assertEqual(port.slices, 0)

    def test_model_import_uses_local_path(self):
        executor, port, _ = build()
        reply = executor.execute("apply_changes", {"operations": [{"kind": "import_model", "path": "/tmp/part.stl"}]})
        self.assertTrue(reply["ok"])
        self.assertEqual(port.applied[0]["path"], "/tmp/part.stl")


if __name__ == "__main__":
    unittest.main()
