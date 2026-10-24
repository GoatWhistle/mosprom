from ..execution.errors import OperationError
from ..protocol import constants
from .pdf_objects import PdfObjects
from .pdf_syntax import Ref
from .pdf_fonts import load_font
from .pdf_text import PageText

MAX_FORM_DEPTH = 4


def _fonts(objects, resources, cache):
    fonts = objects.resolve(resources.get("Font")) if isinstance(resources, dict) else None
    fonts = fonts if isinstance(fonts, dict) else {}

    def font(name):
        reference = fonts.get(str(name))
        key = reference.number if isinstance(reference, Ref) else str(name)
        if key not in cache:
            cache[key] = load_font(objects, reference)
        return cache[key]

    return font


def page_text(objects, resources, data, cache, depth=0):
    lookup = _fonts(objects, resources, cache)
    xobjects = objects.resolve(resources.get("XObject")) if isinstance(resources, dict) else None
    xobjects = xobjects if isinstance(xobjects, dict) else {}

    def form(name):
        reference = xobjects.get(str(name))
        header = objects.resolve(reference)
        if depth >= MAX_FORM_DEPTH or not isinstance(header, dict) or header.get("Subtype") != "Form":
            return ""
        content = objects.stream(reference)
        if content is None:
            return ""
        inner = objects.resolve(header.get("Resources")) or resources
        return page_text(objects, inner, content, cache, depth + 1)

    return PageText(lookup, form).run(data)


def read_pdf(data, pages=None):
    if b"/Encrypt" in data:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "the PDF is encrypted; its text cannot be read")
    objects = PdfObjects(data)
    found = objects.pages()
    if not found:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "no pages were found in the PDF")
    first, last = pages or (1, len(found))
    blocks = []
    warnings = []
    unmapped = 0
    for number in range(max(first, 1), min(last, len(found)) + 1):
        page, resources = found[number - 1]
        cache = {}
        text = page_text(objects, resources, objects.contents(page), cache)
        unmapped += sum(font.unmapped for font in cache.values())
        blocks.append("## Page %d\n\n%s" % (number, text or "[no extractable text]"))
    if unmapped:
        warnings.append("%d glyphs have no Unicode mapping and were skipped" % unmapped)
    if not any(not block.endswith("[no extractable text]") for block in blocks):
        raise OperationError(constants.ERR_NOT_AVAILABLE,
                             "the PDF has no extractable text (scanned pages or unsupported fonts)")
    return {"text": "\n\n".join(blocks), "pages": len(found), "warnings": warnings}
