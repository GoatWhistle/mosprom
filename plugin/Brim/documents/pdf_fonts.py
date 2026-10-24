from .pdf_syntax import Keyword, parse

MAX_RANGE = 65536


class Font(object):
    def __init__(self, mapping=None, lengths=None, single_byte="cp1252", widths=None, default_width=500, scale=1.0):
        self._mapping = mapping or {}
        self._lengths = sorted(set(lengths or [1]), reverse=True)
        self._single_byte = single_byte
        self._widths = widths or {}
        self._default = default_width
        self._scale = scale
        self.unmapped = 0

    def _width(self, code):
        return self._widths.get(int.from_bytes(code, "big"), self._default) * self._scale

    def decode(self, data):
        if not self._mapping:
            width = sum(self._width(data[index:index + 1]) for index in range(len(data)))
            if self._single_byte is None:
                self.unmapped += len(data)
                return "", width
            return data.decode(self._single_byte, "replace"), width
        out = []
        width = 0.0
        index = 0
        while index < len(data):
            for length in self._lengths:
                code = data[index:index + length]
                text = self._mapping.get(code)
                if text is not None:
                    out.append(text)
                    width += self._width(code)
                    index += length
                    break
            else:
                self.unmapped += 1
                width += self._width(data[index:index + self._lengths[-1]])
                index += self._lengths[-1]
        return "".join(out), width


def _utf16(data):
    return data.decode("utf-16-be", "replace") if len(data) % 2 == 0 else data.decode("latin-1")


def _increment(data, step):
    number = int.from_bytes(data, "big") + step
    return number.to_bytes(len(data), "big")


def parse_cmap(data):
    items, _, _ = parse(data)
    mapping = {}
    lengths = []
    section = None
    pending = []
    for item in items:
        if isinstance(item, Keyword):
            if item in ("begincodespacerange", "beginbfchar", "beginbfrange"):
                section, pending = item, []
            elif item.startswith("end"):
                section = None
            continue
        if section is None:
            continue
        pending.append(item)
        if section == "begincodespacerange" and len(pending) == 2:
            if isinstance(pending[0], bytes):
                lengths.append(len(pending[0]))
            pending = []
        elif section == "beginbfchar" and len(pending) == 2:
            if isinstance(pending[0], bytes) and isinstance(pending[1], bytes):
                mapping[pending[0]] = _utf16(pending[1])
            pending = []
        elif section == "beginbfrange" and len(pending) == 3:
            low, high, target = pending
            pending = []
            if not isinstance(low, bytes) or not isinstance(high, bytes) or len(low) != len(high):
                continue
            count = int.from_bytes(high, "big") - int.from_bytes(low, "big") + 1
            for offset in range(max(0, min(count, MAX_RANGE))):
                code = _increment(low, offset)
                if isinstance(target, list):
                    if offset < len(target) and isinstance(target[offset], bytes):
                        mapping[code] = _utf16(target[offset])
                elif isinstance(target, bytes) and target:
                    mapping[code] = _utf16(_increment(target, offset)) if len(target) >= 2 else chr(target[-1] + offset)
    if not lengths:
        lengths = sorted(set(len(code) for code in mapping)) or [1]
    return mapping, lengths


def number(value, default):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else default


def _simple_widths(objects, font):
    first = number(font.get("FirstChar"), 0)
    widths = objects.resolve(font.get("Widths"))
    if not isinstance(widths, list):
        return {}
    return dict((first + index, number(objects.resolve(value), 0)) for index, value in enumerate(widths))


def _cid_widths(objects, font):
    descendants = objects.resolve(font.get("DescendantFonts"))
    descendant = objects.resolve(descendants[0]) if isinstance(descendants, list) and descendants else None
    if not isinstance(descendant, dict):
        return {}, 1000
    items = objects.resolve(descendant.get("W"))
    items = items if isinstance(items, list) else []
    widths = {}
    index = 0
    while index + 1 < len(items):
        first, second = objects.resolve(items[index]), objects.resolve(items[index + 1])
        if isinstance(second, list) and isinstance(first, int):
            for offset, value in enumerate(second):
                widths[first + offset] = number(objects.resolve(value), 0)
            index += 2
        elif index + 2 < len(items) and isinstance(first, int) and isinstance(second, int):
            value = number(objects.resolve(items[index + 2]), 0)
            for code in range(first, min(second, first + MAX_RANGE) + 1):
                widths[code] = value
            index += 3
        else:
            break
    return widths, number(descendant.get("DW"), 1000)


def load_font(objects, font):
    font = objects.resolve(font)
    if not isinstance(font, dict):
        return Font()
    cid = font.get("Subtype") == "Type0"
    if cid:
        widths, default = _cid_widths(objects, font)
    else:
        widths, default = _simple_widths(objects, font), 500
    matrix = objects.resolve(font.get("FontMatrix"))
    scale = number(matrix[0], 0.001) * 1000 if font.get("Subtype") == "Type3" and isinstance(matrix, list) else 1.0
    metrics = {"widths": widths, "default_width": default, "scale": scale}
    cmap = font.get("ToUnicode")
    data = objects.stream(cmap) if cmap is not None else None
    if data is not None:
        mapping, lengths = parse_cmap(data)
        if mapping:
            return Font(mapping, lengths, **metrics)
    if cid:
        return Font(single_byte=None, lengths=[2], **metrics)
    encoding = objects.resolve(font.get("Encoding"))
    return Font(single_byte="latin-1" if encoding == "MacRomanEncoding" else "cp1252", **metrics)
