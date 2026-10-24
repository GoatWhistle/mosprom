import re

from ..execution.errors import OperationError
from ..protocol import constants
from .delimited import select_rows
from .ooxml import OFFICE_REL, open_package, part, relationships
from .tables import markdown_table

S = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
WORKBOOK = "xl/workbook.xml"
CELL_REF = re.compile(r"^([A-Z]+)(\d+)$")
MAX_COLUMNS = 64


def _column(letters):
    number = 0
    for letter in letters:
        number = number * 26 + ord(letter) - 64
    return number - 1


def _shared(package):
    root = part(package, "xl/sharedStrings.xml")
    if root is None:
        return []
    return ["".join(node.text or "" for node in item.iter(S + "t")) for item in root.findall(S + "si")]


def _value(cell, shared):
    kind = cell.get("t")
    if kind == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(S + "t"))
    raw = cell.find(S + "v")
    text = raw.text if raw is not None and raw.text is not None else ""
    if kind == "s":
        try:
            return shared[int(text)]
        except (ValueError, IndexError):
            return ""
    if kind == "b":
        return "TRUE" if text == "1" else "FALSE"
    return text


def _rows(sheet, shared):
    rows = []
    for row in sheet.iter(S + "row"):
        values = {}
        for index, cell in enumerate(row.findall(S + "c")):
            match = CELL_REF.match(cell.get("r") or "")
            column = _column(match.group(1)) if match else index
            if column < MAX_COLUMNS:
                values[column] = _value(cell, shared)
        number = int(row.get("r")) if (row.get("r") or "").isdigit() else len(rows) + 1
        while len(rows) < number - 1:
            rows.append([])
        rows.append([values.get(column, "") for column in range(max(values) + 1)] if values else [])
    return rows


def _sheets(package):
    root = part(package, WORKBOOK)
    if root is None:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "xl/workbook.xml is missing")
    links = relationships(package, WORKBOOK)
    return [(item.get("name"), links.get(item.get(OFFICE_REL + "id")))
            for item in root.iter(S + "sheet")]


def read_xlsx(path, sheet=None, rows=None):
    with open_package(path) as package:
        sheets = _sheets(package)
        names = [name for name, _ in sheets]
        chosen = [item for item in sheets if sheet is None or item[0] == sheet]
        if not chosen:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "no sheet %s; sheets: %s" % (sheet, ", ".join(names)))
        shared = _shared(package)
        blocks = []
        counts = {}
        for name, target in chosen:
            root = part(package, target) if target else None
            table = _rows(root, shared) if root is not None else []
            counts[name] = len(table)
            blocks.append("## %s\n\n%s" % (name, markdown_table(select_rows(table, rows))))
    return {"text": "\n\n".join(blocks), "sheets": names, "rows": counts}
