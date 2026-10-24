WHITESPACE = frozenset(b"\x00\t\n\x0c\r ")
DELIMITERS = frozenset(b"()<>[]{}/%")
ESCAPES = {0x6E: b"\n", 0x72: b"\r", 0x74: b"\t", 0x62: b"\b", 0x66: b"\x0c"}


class Name(str):
    pass


class Keyword(str):
    pass


class Ref(object):
    __slots__ = ("number",)

    def __init__(self, number):
        self.number = number


def _literal(data, index):
    depth = 1
    out = bytearray()
    length = len(data)
    while index < length:
        byte = data[index]
        if byte == 0x5C:
            index += 1
            if index >= length:
                break
            byte = data[index]
            if byte in ESCAPES:
                out += ESCAPES[byte]
            elif 0x30 <= byte <= 0x37:
                digits = data[index:index + 3]
                count = 1
                while count < len(digits) and 0x30 <= digits[count] <= 0x37:
                    count += 1
                out.append(int(digits[:count], 8) & 0xFF)
                index += count - 1
            elif byte == 0x0D:
                if data[index + 1:index + 2] == b"\n":
                    index += 1
            elif byte != 0x0A:
                out.append(byte)
        elif byte == 0x28:
            depth += 1
            out.append(byte)
        elif byte == 0x29:
            depth -= 1
            if depth == 0:
                return bytes(out), index + 1
            out.append(byte)
        else:
            out.append(byte)
        index += 1
    return bytes(out), index


def _hex(data, index):
    end = data.find(b">", index)
    end = len(data) if end < 0 else end
    digits = bytes(byte for byte in data[index:end] if byte not in WHITESPACE)
    if len(digits) % 2:
        digits += b"0"
    try:
        return bytes(bytearray.fromhex(digits.decode("ascii"))), end + 1
    except ValueError:
        return b"", end + 1


def _name(raw):
    out = bytearray()
    index = 0
    while index < len(raw):
        if raw[index] == 0x23 and index + 2 < len(raw):
            try:
                out.append(int(raw[index + 1:index + 3], 16))
                index += 3
                continue
            except ValueError:
                pass
        out.append(raw[index])
        index += 1
    return Name(bytes(out).decode("latin-1"))


def _number(raw):
    try:
        return int(raw)
    except ValueError:
        try:
            return float(raw)
        except ValueError:
            return None


def tokens(data, index=0):
    length = len(data)
    while index < length:
        byte = data[index]
        if byte in WHITESPACE:
            index += 1
        elif byte == 0x25:
            while index < length and data[index] not in (0x0A, 0x0D):
                index += 1
        elif byte == 0x28:
            value, index = _literal(data, index + 1)
            yield "value", value, index
        elif data.startswith(b"<<", index):
            index += 2
            yield "open_dict", None, index
        elif data.startswith(b">>", index):
            index += 2
            yield "close_dict", None, index
        elif byte == 0x3C:
            value, index = _hex(data, index + 1)
            yield "value", value, index
        elif byte == 0x5B:
            index += 1
            yield "open_array", None, index
        elif byte == 0x5D:
            index += 1
            yield "close_array", None, index
        elif byte in (0x7B, 0x7D, 0x3E, 0x29):
            index += 1
        else:
            start = index + 1 if byte == 0x2F else index
            index = start
            while index < length and data[index] not in WHITESPACE and data[index] not in DELIMITERS:
                index += 1
            raw = data[start:index]
            if byte == 0x2F:
                yield "value", _name(raw), index
                continue
            number = _number(raw)
            if number is not None:
                yield "value", number, index
            else:
                yield "keyword", Keyword(raw.decode("latin-1")), index


def _push(container, value):
    if isinstance(value, Keyword) and value == "R" and len(container) >= 2 \
            and isinstance(container[-1], int) and isinstance(container[-2], int):
        container[-2:] = [Ref(container[-2])]
        return
    container.append(value)


def _close(stack):
    items = stack.pop()
    if not isinstance(items, dict):
        return items
    values = items["items"]
    result = {}
    for position in range(0, len(values) - 1, 2):
        if isinstance(values[position], Name):
            result[str(values[position])] = values[position + 1]
    return result


def parse(data, index=0, stop=()):
    stack = [[]]
    for kind, value, end in tokens(data, index):
        if kind == "open_array":
            stack.append([])
        elif kind == "open_dict":
            stack.append({"items": []})
        elif kind in ("close_array", "close_dict"):
            if len(stack) > 1:
                closed = _close(stack)
                _push(_items(stack[-1]), closed)
        elif kind == "keyword" and len(stack) == 1 and value in stop:
            return stack[0], value, end
        else:
            _push(_items(stack[-1]), value)
    while len(stack) > 1:
        closed = _close(stack)
        _push(_items(stack[-1]), closed)
    return stack[0], None, len(data)


def _items(container):
    return container["items"] if isinstance(container, dict) else container
