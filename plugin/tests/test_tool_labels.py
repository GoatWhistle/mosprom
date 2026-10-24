import io
import json
import os
import re
import unittest

from tests import support
from Brim.ui.strings import STRINGS

BRIM_DIR = os.path.join(support.PLUGIN_ROOT, "Brim")
TOOL_CONSTANT = re.compile(r'^(?:NAME|TOOL_[A-Z_]+)\s*=\s*"([a-z][a-z_]*)"', re.M)
NOT_ROWS = {"ask_user"}


def tool_names():
    with io.open(os.path.join(BRIM_DIR, "protocol", "tools.json"), encoding="utf-8") as handle:
        data = json.load(handle)
    items = data if isinstance(data, list) else data.get("tools", [])
    names = set(item.get("name") for item in items if isinstance(item, dict) and item.get("name"))
    for folder, _, files in os.walk(BRIM_DIR):
        for name in files:
            if name.endswith(".py"):
                with io.open(os.path.join(folder, name), encoding="utf-8") as handle:
                    names.update(TOOL_CONSTANT.findall(handle.read()))
    return sorted(names - NOT_ROWS)


class ToolLabelTests(unittest.TestCase):
    def test_every_tool_has_labels_in_both_languages(self):
        missing = []
        for language, strings in sorted(STRINGS.items()):
            for name in tool_names():
                for key in ("tool_" + name, "tool_active_" + name):
                    if key not in strings:
                        missing.append("%s: %s" % (language, key))
        self.assertEqual([], missing)
