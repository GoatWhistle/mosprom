import os
import re
import unittest

from tests import web_styles as ws

BREAKPOINTS = {"30rem", "48rem", "64rem", "75rem", "90rem", "120rem",
               "29.99rem", "47.99rem", "63.99rem", "74.99rem", "89.99rem", "119.99rem"}
LENGTH = re.compile(r"(?<![\w.-])\d*\.?\d+(px|rem|em)\b")
TOKEN_ONLY = {
    "font-size": "--font-size-", "line-height": "--line-height-", "font-weight": "--weight-",
    "font-family": "--font-", "letter-spacing": "--tracking-", "z-index": "--layer-",
    "font-variant-numeric": "--font-numeric", "font-feature-settings": "--font-features",
}
MOTION = re.compile(r"^(none|var\(--(transition|motion)-[\w-]+\))$")
SHADOW = re.compile(r"^(none|var\(--shadow-[\w-]+\))$")
HOVER_GATE = re.compile(r"\(hover:\s*hover\)\s+and\s+\(pointer:\s*fine\)")
NAMED_COLOR = re.compile(r"(?<![\w-])(white|black|red|blue|green|gray|grey|orange|yellow)(?![\w-])")
MAX_LINES = 250
TEXT_SURFACES = ("--surface-base", "--surface-raised", "--surface-sunken")
EXEMPT_TEXT = {"--text-disabled", "--text-on-user"}


def relative(path):
    return os.path.relpath(path, ws.WEB_DIR)


class WebDesignSystemTests(unittest.TestCase):
    def assertClean(self, problems):
        self.assertEqual([], problems, "\n" + "\n".join(problems))

    def test_component_styles_take_values_from_tokens(self):
        problems = []
        for path in ws.component_styles():
            for preludes, prop, value in ws.rules(ws.read(path)):
                where = "%s: %s: %s" % (relative(path), prop, value)
                if ws.HEX.search(value) or re.search(r"\b(rgba?|hsla?|oklch|lab)\(", value) or NAMED_COLOR.search(value):
                    problems.append("color literal " + where)
                if LENGTH.search(re.sub(r"var\([^()]*\)", "", value)):
                    problems.append("length literal " + where)
                prefix = TOKEN_ONLY.get(prop)
                if prefix and not re.match(r"^(inherit|var\(%s[\w-]*\))$" % re.escape(prefix), value):
                    problems.append("token required " + where)
                if prop in ("transition", "animation") and not MOTION.match(value):
                    problems.append("motion token required " + where)
                if prop.startswith(("transition-", "animation-duration", "animation-timing")):
                    problems.append("motion longhand " + where)
                if prop.endswith("shadow") and not SHADOW.match(value):
                    problems.append("shadow token required " + where)
                if "!important" in value or "gradient(" in value or prop == "backdrop-filter":
                    problems.append("forbidden decoration " + where)
                if prop == "text-transform" and not any(".telemetry" in item for item in preludes):
                    problems.append("caps outside telemetry " + where)
        self.assertClean(problems)

    def test_media_queries_use_shared_breakpoints(self):
        problems = []
        for path in ws.web_files(".css"):
            for query in re.findall(r"@media([^{]+)\{", ws.read(path)):
                for amount, unit in re.findall(r"(\d*\.?\d+)(px|rem|em)", query):
                    if amount + unit not in BREAKPOINTS:
                        problems.append("%s: %s" % (relative(path), query.strip()))
        self.assertClean(problems)

    def test_hover_is_gated_to_fine_pointers(self):
        problems = []
        for path in ws.web_files(".css"):
            for preludes, _ in ws.declarations(ws.read(path)):
                if preludes and ":hover" in preludes[-1] and not any(HOVER_GATE.search(item) for item in preludes):
                    problems.append("%s: %s" % (relative(path), preludes[-1]))
        self.assertClean(sorted(set(problems)))

    def test_every_variable_is_defined(self):
        defined = ws.defined_properties()
        problems = []
        for path in ws.web_files(".css") + ws.web_files(".js"):
            for name, fallback in ws.VAR_CALL.findall(ws.read(path)):
                if name not in defined and not fallback:
                    problems.append("%s: %s" % (relative(path), name))
        self.assertClean(sorted(set(problems)))

    def test_scripts_hold_no_design_values(self):
        problems = []
        for path in ws.web_files(".js"):
            text = ws.read(path)
            for literal in ws.HEX.findall(text):
                problems.append("%s: color %s" % (relative(path), literal))
            for literal in re.findall(r"cubic-bezier\([^)]*\)|\b\d+ms\b", text):
                problems.append("%s: motion %s" % (relative(path), literal))
        self.assertClean(problems)

    def test_files_are_short_and_uncommented(self):
        problems = []
        for path in ws.web_files(".css") + ws.web_files(".js") + ws.web_files(".html"):
            text = ws.read(path)
            if text.count("\n") > MAX_LINES:
                problems.append("%s: %d lines" % (relative(path), text.count("\n")))
            if "/*" in text or "<!--" in text or re.search(r"^\s*//", text, re.M):
                problems.append("%s: comment" % relative(path))
        self.assertClean(problems)

    def test_used_classes_exist_in_styles(self):
        known = ws.css_classes()
        problems = ["%s: .%s" % item for item in ws.used_classes() if item[1] not in known]
        self.assertClean(sorted(set(problems)))

    def test_themes_define_the_same_tokens(self):
        tables = ws.theme_tables()
        self.assertEqual(sorted(tables["light"]), sorted(tables["dark"]))

    def test_theme_contrast(self):
        colors = ws.palette()
        tables = ws.theme_tables()
        problems = []
        for theme, table in sorted(tables.items()):
            pairs = []
            for name in table:
                if name.startswith("--text-") and name not in EXEMPT_TEXT:
                    pairs.extend((name, surface, 4.5) for surface in TEXT_SURFACES)
                if name.startswith("--status-"):
                    pairs.extend((name, surface, 3.0) for surface in TEXT_SURFACES)
            pairs.extend([("--text-on-user", "--surface-user", 4.5), ("--focus-ring", "--surface-base", 3.0),
                          ("--focus-ring", "--surface-raised", 3.0), ("--action-primary", "--surface-base", 3.0)])
            pairs.extend(("--action-primary-text", back, 4.5)
                         for back in ("--action-primary", "--action-primary-hover", "--action-primary-press"))
            for front, back, minimum in pairs:
                first, second = ws.resolve(front, table, colors), ws.resolve(back, table, colors)
                if first is None or second is None:
                    continue
                ratio = ws.contrast(first, second)
                if ratio < minimum:
                    problems.append("%s %s on %s: %.2f < %.1f" % (theme, front, back, ratio, minimum))
        self.assertClean(problems)
