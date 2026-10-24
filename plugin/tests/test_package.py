import json
import os
import tempfile
import unittest
import zipfile

from tests import support
import build


class PackageTests(unittest.TestCase):
    def test_archive_has_one_brim_folder_with_required_files(self):
        target = build.build(tempfile.mkdtemp())
        with zipfile.ZipFile(target) as archive:
            names = archive.namelist()
        self.assertTrue(all(name.startswith("Brim/") for name in names))
        for required in ("Brim/plugin.json", "Brim/__init__.py", "Brim/BrimExtension.py", "Brim/protocol/tools.json",
                         "Brim/ui/qml/Chat.qml"):
            self.assertIn(required, names)
        self.assertFalse([name for name in names if "__pycache__" in name or name.endswith(".pyc")])
        self.assertFalse([name for name in names if "tests" in name.split("/") or name.endswith("fakeserver.py")])

    def test_plugin_json_targets_api_5(self):
        with open(os.path.join(support.PLUGIN_ROOT, "Brim", "plugin.json"), encoding="utf-8") as handle:
            meta = json.load(handle)
        self.assertEqual(meta["api"], 5)
        self.assertEqual(meta["name"], "Brim")

    def test_every_qml_component_is_shipped(self):
        folder = os.path.join(support.PLUGIN_ROOT, "Brim", "ui", "qml")
        target = build.build(tempfile.mkdtemp())
        with zipfile.ZipFile(target) as archive:
            names = set(archive.namelist())
        for root, _, files in os.walk(folder):
            for name in files:
                relative = os.path.relpath(os.path.join(root, name), folder).replace(os.sep, "/")
                self.assertIn("Brim/ui/qml/" + relative, names)


if __name__ == "__main__":
    unittest.main()
