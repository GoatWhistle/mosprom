from .pdf_fonts import Font, number
from .pdf_syntax import Keyword, parse

SPACE_RATIO = 0.2


class PageText(object):
    def __init__(self, fonts, forms=None):
        self._fonts = fonts
        self._forms = forms
        self._font = Font()
        self._size = 12.0
        self._leading = 0.0
        self._lines = [[]]
        self._line = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        self._x = 0.0
        self._y = None
        self._end = None

    def _scale(self):
        return abs(self._line[0]) or abs(self._line[1]) or 1.0

    def _newline(self):
        if self._lines[-1]:
            self._lines.append([])
        self._end = None

    def _space(self):
        line = self._lines[-1]
        if line and not line[-1].endswith(" "):
            line.append(" ")

    def _move(self, matrix):
        self._line = matrix
        x, y = matrix[4], matrix[5]
        threshold = SPACE_RATIO * self._size * (abs(matrix[3]) or abs(matrix[2]) or 1.0)
        if self._y is not None and abs(y - self._y) > threshold:
            self._newline()
        self._x, self._y = x, y

    def _translate(self, tx, ty):
        a, b, c, d, e, f = self._line
        self._move([a, b, c, d, e + tx * a + ty * c, f + tx * b + ty * d])

    def _advance(self, units):
        self._x += units / 1000.0 * self._size * self._scale()

    def _show(self, value):
        if isinstance(value, bytes):
            gap = SPACE_RATIO * self._size * self._scale()
            if self._end is not None and (self._x - self._end > gap or self._end - self._x > self._size * self._scale()):
                self._space()
            text, width = self._font.decode(value)
            self._lines[-1].append(text)
            self._advance(width)
            self._end = self._x
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, (int, float)):
                    self._advance(-item)
                else:
                    self._show(item)

    def run(self, data):
        items, _, _ = parse(data)
        operands = []
        for item in items:
            if not isinstance(item, Keyword):
                operands.append(item)
                continue
            self._operator(item, operands)
            operands = []
        return "\n".join("".join(line).strip() for line in self._lines if "".join(line).strip())

    def _numbers(self, operands, count):
        values = operands[-count:]
        if len(values) < count or not all(isinstance(item, (int, float)) for item in values):
            return None
        return [float(item) for item in values]

    def _operator(self, name, operands):
        if name == "BT":
            self._line = [1.0, 0.0, 0.0, 1.0, 0.0, 0.0]
            self._x = 0.0
        elif name == "Tf" and len(operands) >= 2:
            self._font = self._fonts(operands[-2])
            self._size = abs(number(operands[-1], 12.0)) or 12.0
        elif name == "TL" and operands:
            self._leading = number(operands[-1], 0.0)
        elif name in ("Td", "TD"):
            values = self._numbers(operands, 2)
            if values is not None:
                if name == "TD":
                    self._leading = -values[1]
                self._translate(values[0], values[1])
        elif name == "Tm":
            values = self._numbers(operands, 6)
            if values is not None:
                self._move(values)
        elif name == "T*":
            self._translate(0.0, -self._leading)
            self._newline()
        elif name in ("Tj", "TJ") and operands:
            self._show(operands[-1])
        elif name in ("'", '"') and operands:
            self._translate(0.0, -self._leading)
            self._newline()
            self._show(operands[-1])
        elif name == "Do" and operands and self._forms is not None:
            text = self._forms(operands[0])
            if text:
                self._newline()
                self._lines[-1].append(text)
                self._newline()
