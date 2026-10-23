import os
import tempfile
import unittest

from tests import support
from Brim.execution.artifacts import ArtifactService, file_sha256
from Brim.execution.attachments import AttachmentCache
from Brim.execution.executor import ToolExecutor
from Brim.execution.geometry import analyze
from Brim.execution.ledger import CallLedger


def build(ledger_path=None):
    directory = tempfile.mkdtemp()
    port = support.FakePort()
    http = support.FakeHttp()
    ledger = CallLedger(ledger_path)
    executor = ToolExecutor(port, ledger, AttachmentCache(http, directory), ArtifactService(http, os.path.join(directory, "art")))
    return executor, port, http, ledger, directory


def call(call_id, tool, arguments, expected=None, run_id="run-1"):
    return {"type": "tool_call", "id": "f-" + call_id, "call_id": call_id, "run_id": run_id, "tool": tool,
            "arguments": arguments, "expected_scene_version": expected}


class ExecutorTests(unittest.TestCase):
    def test_apply_changes_runs_in_order_and_restores_autoslicing(self):
        executor, port, _, _, _ = build()
        ops = [{"kind": "select_mode", "mode": "classic"}, {"kind": "arrange"}]
        reply = executor.execute_call(call("c1", "apply_changes", {"operations": ops}, expected=1))
        self.assertTrue(reply["ok"])
        self.assertEqual([item["kind"] for item in port.applied], ["select_mode", "arrange"])
        self.assertEqual([item["kind"] for item in reply["applied"]], ["select_mode", "arrange"])
        self.assertEqual(port.batches, 0)

    def test_stale_scene_changes_nothing(self):
        executor, port, _, _, _ = build()
        reply = executor.execute_call(call("c1", "apply_changes", {"operations": [{"kind": "arrange"}]}, expected=7))
        self.assertFalse(reply["ok"])
        self.assertEqual(reply["error"]["code"], "stale_scene")
        self.assertEqual(port.applied, [])

    def test_repeated_call_returns_stored_result_without_reapplying(self):
        executor, port, _, _, _ = build()
        message = call("c1", "apply_changes", {"operations": [{"kind": "arrange"}]})
        first = executor.execute_call(message)
        second = executor.execute_call(message)
        self.assertEqual(first, second)
        self.assertEqual(len(port.applied), 1)

    def test_same_call_id_with_other_content_is_rejected(self):
        executor, port, _, _, _ = build()
        executor.execute_call(call("c1", "apply_changes", {"operations": [{"kind": "arrange"}]}))
        reply = executor.execute_call(call("c1", "apply_changes", {"operations": [{"kind": "delete", "object_ids": ["a"]}]}))
        self.assertEqual(reply["error"]["code"], "call_id_conflict")
        self.assertEqual(len(port.applied), 1)

    def test_partial_batch_reports_applied_and_stops(self):
        executor, port, _, _, _ = build()
        port.fail_on = "arrange"
        ops = [{"kind": "select_mode", "mode": "classic"}, {"kind": "arrange"}, {"kind": "select_mode", "mode": "cylindrical"}]
        reply = executor.execute_call(call("c1", "apply_changes", {"operations": ops}))
        self.assertFalse(reply["ok"])
        self.assertEqual(len(reply["applied"]), 1)
        self.assertEqual(reply["result"]["failed_index"], 1)
        self.assertEqual(len(port.applied), 1)
        self.assertEqual(port.batches, 0)

    def test_invalid_arguments_are_rejected_before_any_change(self):
        executor, port, _, _, _ = build()
        reply = executor.execute_call(call("c1", "apply_changes", {"operations": [{"kind": "select_mode", "mode": "x"}]}))
        self.assertEqual(reply["error"]["code"], "invalid_arguments")
        self.assertEqual(port.applied, [])

    def test_cancel_stops_remaining_operations(self):
        executor, port, _, _, _ = build()
        executor.cancel_run("run-1")
        reply = executor.execute_call(call("c1", "apply_changes", {"operations": [{"kind": "arrange"}]}))
        self.assertEqual(reply["error"]["code"], "cancelled")
        self.assertEqual(port.applied, [])

    def test_unknown_tool(self):
        executor, _, _, _, _ = build()
        reply = executor.execute_call(call("c1", "ask_user", {}))
        self.assertEqual(reply["error"]["code"], "unknown_tool")

    def test_read_tools(self):
        executor, _, _, _, _ = build()
        self.assertEqual(executor.execute_call(call("a", "search_settings", {"query": "wall"}))["result"]["matches"][0]["query"], "wall")
        self.assertEqual(executor.execute_call(call("b", "inspect_profile", {}))["result"], {"profile": "fine"})
        self.assertFalse(executor.execute_call(call("c", "search_settings", {"query": " "}))["ok"])
        self.assertEqual(executor.execute_call(call("d", "render_scene", {}))["result"], {"view": "iso"})

    def test_analyze_geometry_cube(self):
        executor, _, _, _, _ = build()
        reply = executor.execute_call(call("c1", "analyze_geometry", {"object_ids": ["obj-1"], "direction": [0, 0, 1]}))
        info = reply["result"]["objects"]["obj-1"]
        self.assertTrue(info["closed"])
        self.assertAlmostEqual(info["volume_mm3"], 1000.0, places=3)
        self.assertAlmostEqual(info["surface_area_mm2"], 600.0, places=3)
        self.assertEqual(info["connected_components"], 1)
        self.assertEqual(info["bed_contact_area_mm2"], 100.0)
        missing = executor.execute_call(call("c2", "analyze_geometry", {"object_ids": ["nope"]}))
        self.assertFalse(missing["ok"])
        self.assertFalse(executor.execute_call(call("c3", "analyze_geometry", {"object_ids": ["obj-1"], "direction": [0, 0, 0]}))["ok"])

    def test_open_mesh_has_no_volume(self):
        mesh = support.cube_mesh()
        mesh["triangles"] = mesh["triangles"][:-1]
        info = analyze(mesh)
        self.assertFalse(info["closed"])
        self.assertIsNone(info["volume_mm3"])

    def test_slice_uploads_both_files_and_reuses_them_after_failure(self):
        executor, port, http, _, _ = build()
        http.fail_upload = 1
        failed = executor.execute_call(call("c1", "slice", {}))
        self.assertEqual(failed["error"]["code"], "upload_failed")
        self.assertEqual(port.slices, 1)
        retried = executor.execute_call(call("c2", "slice", {}))
        self.assertTrue(retried["ok"])
        self.assertEqual(port.slices, 1)
        self.assertEqual(port.exports, 1)
        self.assertTrue(all(item["uploaded"] for item in retried["result"]["artifacts"].values()))
        self.assertEqual(sorted(http.chunks), ["3mf", "gcode"])

    def test_slice_discards_result_when_scene_changes(self):
        executor, port, http, _, _ = build()
        port.bump_on_slice = True
        reply = executor.execute_call(call("c1", "slice", {}))
        self.assertEqual(reply["error"]["code"], "stale_result")
        self.assertEqual(http.calls, [])

    def test_slice_chunks_large_files(self):
        executor, port, http, _, directory = build()
        original = port.export_artifacts

        def big(target):
            paths = original(target)
            with open(paths["gcode"], "wb") as handle:
                handle.write(b"x" * (2 * 1024 * 1024 + 5))
            return paths

        port.export_artifacts = big
        reply = executor.execute_call(call("c1", "slice", {}))
        self.assertTrue(reply["ok"])
        self.assertEqual(len(http.chunks["gcode"]), 3)

    def test_attachment_import_downloads_before_applying(self):
        executor, port, http, _, _ = build()
        http.attachments["att-1"] = b"solid"
        op = {"kind": "import_model", "attachment_id": "att-1", "name": "part.stl"}
        reply = executor.execute_call(call("c1", "apply_changes", {"operations": [op]}))
        self.assertTrue(reply["ok"])
        self.assertTrue(os.path.exists(port.applied[0]["path"]))

    def test_mcp_execution(self):
        executor, _, _, _, _ = build()
        outcome = executor.execute_mcp("inspect_profile", {}, 1)
        self.assertTrue(outcome["ok"])


class LedgerTests(unittest.TestCase):
    def test_running_call_becomes_outcome_unknown_after_restart(self):
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "ledger.json")
        ledger = CallLedger(path)
        ledger.begin("c1", "r1", 3)
        restarted = CallLedger(path)
        frame = restarted.result_frame("c1")
        self.assertEqual(frame["error"]["code"], "outcome_unknown")
        self.assertEqual(restarted.running_ids(), [])

    def test_begin_is_atomic_and_rejects_duplicates(self):
        ledger = CallLedger()
        self.assertTrue(ledger.begin("c1", "r1", 1))
        self.assertFalse(ledger.begin("c1", "r1", 1))

    def test_file_hash(self):
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "a")
        with open(path, "wb") as handle:
            handle.write(b"abc")
        self.assertEqual(file_sha256(path), "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")


if __name__ == "__main__":
    unittest.main()
