from .ooxml import OFFICE_REL, open_package, part, relationships
from .tables import markdown_table

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
DOCUMENT = "word/document.xml"
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
MAX_IMAGES = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024


def _run_text(element):
    pieces = []
    for node in element.iter():
        if node.tag == W + "t":
            pieces.append(node.text or "")
        elif node.tag == W + "tab":
            pieces.append("\t")
        elif node.tag in (W + "br", W + "cr"):
            pieces.append("\n")
    return "".join(pieces)


def _style(paragraph):
    properties = paragraph.find(W + "pPr")
    if properties is None:
        return "", False
    style = properties.find(W + "pStyle")
    name = (style.get(W + "val") if style is not None else "") or ""
    return name, properties.find(W + "numPr") is not None


def _heading_level(style):
    lowered = style.lower().replace(" ", "")
    for prefix in ("heading", "заголовок"):
        if lowered.startswith(prefix) and lowered[len(prefix):].isdigit():
            return min(int(lowered[len(prefix):]), 6)
    return 0 if lowered != "title" else 1


def _paragraph(paragraph):
    text = _run_text(paragraph).strip()
    if not text:
        return ""
    style, listed = _style(paragraph)
    level = _heading_level(style)
    if level:
        return "#" * level + " " + text
    return "- " + text if listed else text


def _table(table):
    rows = []
    for row in table.findall(W + "tr"):
        rows.append([" ".join(_paragraph(item) for item in cell.iter(W + "p")).strip()
                     for cell in row.findall(W + "tc")])
    return markdown_table(rows)


def _images(package, body):
    links = relationships(package, DOCUMENT)
    images = []
    for blip in body.iter(A + "blip"):
        target = links.get(blip.get(OFFICE_REL + "embed"))
        extension = "." + target.rsplit(".", 1)[-1].lower() if target and "." in target else ""
        if extension not in IMAGE_TYPES or len(images) >= MAX_IMAGES:
            continue
        info = package.getinfo(target) if target in package.namelist() else None
        if info is None or info.file_size > MAX_IMAGE_BYTES:
            continue
        images.append({"mime_type": IMAGE_TYPES[extension], "data": package.read(info), "name": target})
    return images


def read_docx(path):
    with open_package(path) as package:
        root = part(package, DOCUMENT)
        if root is None:
            return {"text": "", "warnings": ["word/document.xml is missing"]}
        body = root.find(W + "body")
        blocks = []
        for child in list(body) if body is not None else []:
            if child.tag == W + "p":
                blocks.append(_paragraph(child))
            elif child.tag == W + "tbl":
                blocks.append(_table(child))
        images = _images(package, body) if body is not None else []
    return {"text": "\n\n".join(block for block in blocks if block), "images": images}
