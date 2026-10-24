import os

from ..execution.errors import OperationError
from ..protocol import constants
from .delimited import read_delimited
from .docx import read_docx
from .pdf import read_pdf
from .text import read_json, read_text
from .xlsx import read_xlsx

DOCUMENT_TYPES = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".csv": "text/csv", ".tsv": "text/tab-separated-values", ".txt": "text/plain", ".md": "text/markdown",
    ".json": "application/json", ".pdf": "application/pdf",
}
MAX_DOCUMENT_BYTES = 20 * 1024 * 1024
DEFAULT_CHARS = 20000
MAX_CHARS = 60000


def _range(value, name):
    if value is None:
        return None
    if not (isinstance(value, list) and len(value) == 2 and all(isinstance(item, int) and item >= 1 for item in value)
            and value[0] <= value[1]):
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "%s must be [first, last], 1-based" % name)
    return value[0], value[1]


def _data(path):
    with open(path, "rb") as handle:
        return handle.read()


def _parse(path, extension, sheet, rows, pages):
    if extension == ".docx":
        return read_docx(path)
    if extension == ".xlsx":
        return read_xlsx(path, sheet, rows)
    if extension in (".csv", ".tsv"):
        return read_delimited(_data(path), rows)
    if extension == ".pdf":
        return read_pdf(_data(path), pages)
    if extension == ".json":
        return read_json(_data(path))
    return read_text(_data(path))


def read_document(path, start=0, max_chars=None, sheet=None, rows=None, pages=None):
    extension = os.path.splitext(path)[1].lower()
    if extension not in DOCUMENT_TYPES:
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "unsupported document type %s; supported: %s" % (
            extension or "?", ", ".join(sorted(DOCUMENT_TYPES))))
    try:
        size = os.path.getsize(path)
    except OSError as error:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "cannot open %s: %s" % (os.path.basename(path), error))
    if size > MAX_DOCUMENT_BYTES:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "the document is larger than %d MiB" % (
            MAX_DOCUMENT_BYTES // (1024 * 1024)))
    if not isinstance(start, int) or start < 0:
        raise OperationError(constants.ERR_INVALID_ARGUMENTS, "start must be a non-negative integer")
    limit = max_chars if isinstance(max_chars, int) and max_chars > 0 else DEFAULT_CHARS
    limit = min(limit, MAX_CHARS)
    parsed = _parse(path, extension, sheet, _range(rows, "rows"), _range(pages, "pages"))
    text = parsed.pop("text", "")
    images = parsed.pop("images", [])
    end = min(len(text), start + limit)
    result = dict(parsed, name=os.path.basename(path), format=extension[1:], start=start,
                  total_chars=len(text), text=text[start:end], truncated=end < len(text),
                  next_start=end if end < len(text) else None)
    result.setdefault("warnings", [])
    if images:
        result["embedded_images"] = [item["name"] for item in images]
    return result, ([] if start else images)
