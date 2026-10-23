import zipfile
import xml.etree.ElementTree as ET

from ..execution.errors import OperationError
from ..protocol import constants

MODEL_NS = "{http://schemas.microsoft.com/3dmanufacturing/core/2015/02}"


def verify_project(path):
    try:
        with zipfile.ZipFile(path, "r") as archive:
            if archive.testzip() is not None:
                raise ValueError("invalid ZIP checksum")
            model = ET.fromstring(archive.read("3D/3dmodel.model"))
            if not model.findall(".//" + MODEL_NS + "triangle"):
                raise ValueError("project has no mesh triangles")
            if not model.findall("./" + MODEL_NS + "build/" + MODEL_NS + "item"):
                raise ValueError("project has no build items")
            settings = [name for name in archive.namelist()
                        if name.endswith((".global.cfg", ".extruder.cfg", ".inst.cfg"))]
            if not settings:
                raise ValueError("project has no printer settings")
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as error:
        raise OperationError(constants.ERR_OPERATION_FAILED, "invalid 3MF project: %s" % error)


def verify_workspace(path):
    try:
        with zipfile.ZipFile(path, "r") as archive:
            if archive.testzip() is not None:
                raise ValueError("invalid ZIP checksum")
            ET.fromstring(archive.read("3D/3dmodel.model"))
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as error:
        raise OperationError(constants.ERR_OPERATION_FAILED, "invalid workspace file: %s" % error)
