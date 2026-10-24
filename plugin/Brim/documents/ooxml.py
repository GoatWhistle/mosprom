import posixpath
import xml.etree.ElementTree as ElementTree
import zipfile

from ..execution.errors import OperationError
from ..protocol import constants

RELS_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
OFFICE_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
MAX_PART_BYTES = 64 * 1024 * 1024


def open_package(path):
    try:
        return zipfile.ZipFile(path)
    except (zipfile.BadZipfile, OSError) as error:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "not an Office Open XML package: %s" % error)


def part(package, name):
    try:
        info = package.getinfo(name)
    except KeyError:
        return None
    if info.file_size > MAX_PART_BYTES:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "%s is too large to read" % name)
    return ElementTree.fromstring(package.read(info))


def relationships(package, source):
    folder, name = posixpath.split(source)
    root = part(package, posixpath.join(folder, "_rels", name + ".rels"))
    links = {}
    if root is None:
        return links
    for item in root.iter(RELS_NS + "Relationship"):
        target = item.get("Target") or ""
        if item.get("TargetMode") == "External":
            continue
        resolved = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join(folder, target))
        links[item.get("Id")] = resolved
    return links
