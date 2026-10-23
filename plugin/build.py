import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(ROOT, "Brim")
SKIP_DIRS = ("__pycache__",)
SKIP_SUFFIXES = (".pyc", ".pyo")


def version():
    with open(os.path.join(SOURCE, "plugin.json"), "r", encoding="utf-8") as handle:
        return json.load(handle)["version"]


def files():
    for folder, names, items in os.walk(SOURCE):
        names[:] = sorted(name for name in names if name not in SKIP_DIRS)
        for item in sorted(items):
            if not item.endswith(SKIP_SUFFIXES):
                yield os.path.join(folder, item)


def build(output_dir):
    os.makedirs(output_dir, exist_ok=True)
    target = os.path.join(output_dir, "Brim-%s.zip" % version())
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files():
            archive.write(path, os.path.join("Brim", os.path.relpath(path, SOURCE)))
    return target


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist")))
