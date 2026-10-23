import os
import tempfile
import threading
import unittest

from Brim.execution.attachments import AttachmentCache, disposition_name, safe_name
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
    def test_encoded_name_wins_over_ascii_fallback(self):
        header = "attachment; filename=\"________.stl\"; filename*=UTF-8''%D0%A8%D0%B5%D1%81%D1%82%D0%B5%D1%80%D0%BD%D1%8F.stl"
        self.assertEqual(disposition_name(header), "Шестерня.stl")

    def test_plain_name_is_used_without_encoded_one(self):
        self.assertEqual(disposition_name('attachment; filename="part.stl"'), "part.stl")

    def test_windows_unsafe_characters_are_replaced(self):
        self.assertEqual(safe_name('..\\dir/a?b*c:"d|<e>.stl'), "a_b_c__d__e_.stl")

    def test_cyrillic_attachment_is_cached_under_its_name(self):
        class Http(object):
            def download_attachment(self, attachment_id):
                return b"solid", {"Content-Disposition": "attachment; filename=\"________.stl\"; filename*=UTF-8''%D0%A8%D0%B5%D1%81%D1%82%D0%B5%D1%80%D0%BD%D1%8F.stl"}

        with tempfile.TemporaryDirectory() as directory:
            path = AttachmentCache(Http(), directory).fetch("att-1")
            self.assertEqual(os.path.basename(path), "Шестерня.stl")
            with open(path, "rb") as handle:
                self.assertEqual(handle.read(), b"solid")
