import os
import tempfile
import threading
import unittest

from Brim.chat.files import copy_into, describe, safe_name
from Brim.slicer.qt_wrappers import direct_qt_calls, unwrapped


def ste_call_on_qt_thread(func):
    def _call_on_qt_thread_wrapper(*args, **kwargs):
        def _handle_call(ico, *args, **kwargs):
            ico["result"] = func(*args, **kwargs)
            ico["done"].set()

        box = {"done": threading.Event()}
        threading.Thread(target=lambda: None).start()
        if not box["done"].wait(0.05):
            raise RuntimeError("deadlock: wrapper waits for the Qt thread")
        return box["result"]

    return _call_on_qt_thread_wrapper


class ProjectWriter(object):
    @ste_call_on_qt_thread
    def write(self, stream, nodes):
        stream.append(("project", nodes))
        return True


class GCodeWriter(object):
    def write(self, stream, nodes):
        stream.append(self._createSnapshot())
        return True

    @ste_call_on_qt_thread
    def _createSnapshot(self):
        return "snapshot"


class QtWrapperTests(unittest.TestCase):
    def test_ste_wrapper_blocks_when_called_directly(self):
        with self.assertRaises(RuntimeError):
            ProjectWriter().write([], None)

    def test_wrapped_method_is_called_directly(self):
        writer = ProjectWriter()
        stream = []
        with direct_qt_calls(writer, "write"):
            self.assertTrue(writer.write(stream, ["root"]))
        self.assertEqual(stream, [("project", ["root"])])
        self.assertNotIn("write", vars(writer))

    def test_inner_wrapped_call_is_direct_and_restored(self):
        writer = GCodeWriter()
        stream = []
        with direct_qt_calls(writer, "_createSnapshot"):
            writer.write(stream, None)
        self.assertEqual(stream, ["snapshot"])
        self.assertNotIn("_createSnapshot", vars(writer))

    def test_plain_methods_are_left_alone(self):
        writer = GCodeWriter()
        self.assertEqual(unwrapped(writer.write, "write"), writer.write)


class AttachmentNameTests(unittest.TestCase):
    def test_windows_unsafe_characters_are_replaced(self):
        self.assertEqual(safe_name('..\\dir/a?b*c:"d|<e>.stl'), "a_b_c__d__e_.stl")

    def test_cyrillic_attachment_is_copied_under_its_name(self):
        with tempfile.TemporaryDirectory() as directory:
            source = os.path.join(directory, "Шестерня.stl")
            with open(source, "wb") as handle:
                handle.write(b"solid")
            copied = copy_into([describe(source)], os.path.join(directory, "chat"))
            self.assertTrue(os.path.basename(copied[0]["path"]).endswith("-Шестерня.stl"))
            self.assertEqual(copied[0]["kind"], "model")
            with open(copied[0]["path"], "rb") as handle:
                self.assertEqual(handle.read(), b"solid")

    def test_images_are_described_with_mime_type(self):
        self.assertEqual(describe("/tmp/photo.JPG")["mime_type"], "image/jpeg")
        self.assertEqual(describe("/tmp/photo.JPG")["kind"], "image")
