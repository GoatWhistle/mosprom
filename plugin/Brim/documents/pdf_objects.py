import base64
import re
import zlib

from .pdf_syntax import Name, Ref, parse

OBJECT_START = re.compile(rb"(\d+)\s+(\d+)\s+obj\b")
STREAM_END = b"endstream"


def _eol(data, index):
    if data.startswith(b"\r\n", index):
        return index + 2
    if data[index:index + 1] in (b"\n", b"\r"):
        return index + 1
    return index


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


class PdfObjects(object):
    def __init__(self, data):
        self._objects = {}
        self._streams = {}
        self._scan(data)
        self._expand_object_streams()

    def _scan(self, data):
        index = 0
        while True:
            match = OBJECT_START.search(data, index)
            if match is None:
                return
            number = int(match.group(1))
            items, stop, end = parse(data, match.end(), ("stream", "endobj", "obj"))
            if stop == "obj":
                index = match.end()
                continue
            value = items[0] if items else None
            self._objects[number] = value
            index = end
            if stop == "stream":
                start = _eol(data, end)
                length = value.get("Length") if isinstance(value, dict) else None
                finish = start + length if isinstance(length, int) and data.startswith(
                    STREAM_END, _skip_space(data, start + length)) else data.find(STREAM_END, start)
                finish = len(data) if finish < 0 else finish
                self._streams[number] = data[start:finish]
                index = finish + len(STREAM_END)

    def _expand_object_streams(self):
        for number, value in list(self._objects.items()):
            if not isinstance(value, dict) or value.get("Type") != "ObjStm":
                continue
            data = self.stream(number)
            first, count = value.get("First"), value.get("N")
            if data is None or not isinstance(first, int) or not isinstance(count, int):
                continue
            header, _, _ = parse(data[:first])
            for position in range(0, min(len(header), count * 2) - 1, 2):
                inner, offset = header[position], header[position + 1]
                if isinstance(inner, int) and isinstance(offset, int) and inner not in self._objects:
                    items, _, _ = parse(data, first + offset)
                    self._objects[inner] = items[0] if items else None

    def resolve(self, value, depth=0):
        while isinstance(value, Ref) and depth < 32:
            value = self._objects.get(value.number)
            depth += 1
        return value

    def items(self):
        return list(self._objects.items())

    def stream(self, reference):
        number = reference.number if isinstance(reference, Ref) else reference
        raw = self._streams.get(number)
        header = self._objects.get(number)
        if raw is None or not isinstance(header, dict):
            return None
        for name in _as_list(self.resolve(header.get("Filter"))):
            if name in ("FlateDecode", "Fl"):
                try:
                    raw = zlib.decompressobj().decompress(raw)
                except zlib.error:
                    return None
            elif name in ("ASCII85Decode", "A85"):
                try:
                    raw = base64.a85decode(raw.strip().split(b"~>")[0].lstrip(b"<~"))
                except ValueError:
                    return None
            elif name in ("ASCIIHexDecode", "AHx"):
                digits = bytes(byte for byte in raw.split(b">")[0] if chr(byte) in "0123456789abcdefABCDEF")
                raw = bytes(bytearray.fromhex((digits + b"0" * (len(digits) % 2)).decode("ascii")))
            else:
                return None
        return raw

    def pages(self):
        catalog = next((value for _, value in sorted(self.items())
                        if isinstance(value, dict) and value.get("Type") == "Catalog"), None)
        pages = []
        if catalog is not None:
            self._walk(catalog.get("Pages"), {}, pages, set())
        if not pages:
            pages = [(value, value.get("Resources")) for _, value in sorted(self.items())
                     if isinstance(value, dict) and value.get("Type") == "Page"]
        return [(page, self.resolve(resources) or {}) for page, resources in pages]

    def _walk(self, reference, inherited, pages, seen):
        key = reference.number if isinstance(reference, Ref) else id(reference)
        node = self.resolve(reference)
        if not isinstance(node, dict) or key in seen:
            return
        seen.add(key)
        resources = node.get("Resources", inherited.get("Resources"))
        if node.get("Type") == "Page" or "Kids" not in node:
            pages.append((node, resources))
            return
        for kid in _as_list(self.resolve(node.get("Kids"))):
            self._walk(kid, {"Resources": resources}, pages, seen)

    def contents(self, page):
        parts = []
        contents = page.get("Contents")
        resolved = self.resolve(contents)
        for item in resolved if isinstance(resolved, list) else [contents]:
            data = self.stream(item) if isinstance(item, Ref) else None
            if data is not None:
                parts.append(data)
        return b"\n".join(parts)


def _skip_space(data, index):
    while data[index:index + 1] in (b"\r", b"\n", b" ", b"\t"):
        index += 1
    return index
