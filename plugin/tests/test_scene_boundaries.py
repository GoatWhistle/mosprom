import io
import os
import tempfile
import threading
import unittest
import zipfile
from unittest import mock

from Brim.execution.errors import OperationError
from Brim.slicer.main_thread import MainThread
from Brim.slicer.material_catalog import available_materials, inspect_material
from Brim.slicer.project_archive import verify_project
from Brim.slicer.scene_ops import SceneOperations
from Brim.slicer.slicing import SlicingService
from tests.test_slicer_adapters import fake_host

MODEL = b'''<model xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>
<object id="1"><mesh><vertices><vertex x="0" y="0" z="0"/></vertices>
<triangles><triangle v1="0" v2="0" v3="0"/></triangles></mesh></object></resources>
<build><item objectid="1"/></build></model>'''


def archive_bytes(model=True, settings=True):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        if model:
            archive.writestr("3D/3dmodel.model", MODEL)
        if settings:
            archive.writestr("SteSlicer/printer.global.cfg", "[general]\nname = printer")
    return buffer.getvalue()


class ProjectTests(unittest.TestCase):
    def test_project_writer_receives_scene_root_and_archive_is_validated(self):
        host, _ = fake_host()
        main = MainThread(host.application)
        root = object()
        host.scene.return_value.getRoot.return_value = root
        writer = host.application.getWorkspaceFileHandler.return_value.getWriter.return_value

        def write(stream, nodes):
            self.assertEqual(nodes, [root])
            stream.write(archive_bytes())
            return True

        writer.write.side_effect = write
        service = SlicingService(host, main, mock.Mock())
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "project.3mf")
            service._write_project(path)
            verify_project(path)

    def test_missing_geometry_or_settings_is_rejected(self):
        for model, settings in [(False, True), (True, False)]:
            with tempfile.TemporaryDirectory() as folder:
                path = os.path.join(folder, "bad.3mf")
                with open(path, "wb") as handle:
                    handle.write(archive_bytes(model, settings))
                with self.assertRaises(OperationError):
                    verify_project(path)


class MaterialTests(unittest.TestCase):
    def test_catalog_and_inspection_include_inactive_compatible_material(self):
        host, stack = fake_host()
        node = mock.Mock()
        node.getMetadata.return_value = {"name": "ABS", "material": "ABS", "brand": "Generic"}
        container = node.getContainer.return_value
        container.getAllKeys.return_value = ["material_print_temperature"]
        container.getProperty.return_value = 245
        materials = host.application.getMaterialManager.return_value
        materials.getAvailableMaterialsForMachineExtruder.return_value = {"generic_abs": node}
        self.assertEqual(available_materials(host)[0]["material_id"], "generic_abs")
        detail = inspect_material(host, "generic_abs")["materials"][0]
        self.assertEqual(detail["material_settings"]["material_print_temperature"], 245)
        materials.getAvailableMaterialsForMachineExtruder.assert_called_with(stack, stack.extruders["0"])
        with self.assertRaises(OperationError):
            inspect_material(host, "unavailable")


class ThreadBoundaryTests(unittest.TestCase):
    def test_transform_lookup_and_description_run_on_owner_thread(self):
        owner = threading.current_thread()
        app = mock.Mock()
        pending = []
        queued = threading.Event()

        def call_later(function):
            pending.append(function)
            queued.set()

        app.callLater.side_effect = call_later
        access = mock.Mock()
        node = object()

        def require(identifier):
            self.assertIs(threading.current_thread(), owner)
            return node

        def describe(value):
            self.assertIs(threading.current_thread(), owner)
            return {"id": "object"}

        access.require.side_effect = require
        access.describe.side_effect = describe
        ops = SceneOperations(mock.Mock(), access, MainThread(app))
        ops._transform_on_main = mock.Mock()
        results = []
        thread = threading.Thread(target=lambda: results.append(ops.transform({"object_id": "object"})))
        thread.start()
        self.assertTrue(queued.wait(2))
        pending[0]()
        thread.join(2)
        self.assertEqual(results, [{"id": "object"}])
