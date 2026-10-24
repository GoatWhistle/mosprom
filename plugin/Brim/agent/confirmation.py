import json

from ..protocol import constants

MODE_ASK = "ask"
MODE_AUTO = "auto"
SETTING_KINDS = ("set_global_setting", "set_extruder_setting")
SUMMARY_KEYS = ("mode", "profile_id", "material_id", "object_id", "object_ids", "name", "path", "import_as",
                "position_mm", "rotation_deg", "scale", "count", "keys")
DEFAULT_RATIO = 2.0


def _number(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _shown(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _limits(low, high):
    if low is None and high is None:
        return None
    return "%s..%s" % ("" if low is None else _shown(low), "" if high is None else _shown(high))


def _summary(op):
    parts = []
    for key in SUMMARY_KEYS:
        if key in op:
            parts.append("%s: %s" % (key, _shown(op[key])))
    return ", ".join(parts)


class ConfirmationPolicy(object):
    def __init__(self, facts, ratio=None):
        self._facts = facts
        self._ratio = ratio

    def ratio(self):
        value = self._ratio() if callable(self._ratio) else self._ratio
        value = _number(value)
        return value if value is not None and value > 1 else DEFAULT_RATIO

    def review(self, mode, tool, arguments):
        server = tool.get("server")
        annotations = tool.get("annotations") or {}
        if server != "brim":
            if mode == MODE_AUTO and not annotations.get("destructiveHint"):
                return None
            if mode == MODE_ASK and annotations.get("readOnlyHint"):
                return None
            return [{"kind": "external", "target": tool.get("name"), "detail": _shown(arguments),
                     "risky": bool(annotations.get("destructiveHint")), "reason": "destructive" if annotations.get("destructiveHint") else None}]
        name = tool.get("tool")
        if name == constants.TOOL_SLICE:
            return [{"kind": "slice", "target": "", "detail": "", "risky": False, "reason": None}] if mode == MODE_ASK else None
        if name != constants.TOOL_APPLY_CHANGES:
            return None
        items = [self._item(op) for op in arguments.get("operations") or [] if isinstance(op, dict)]
        if mode == MODE_AUTO:
            items = [item for item in items if item["risky"]]
        return items or None

    def _item(self, op):
        kind = op.get("kind")
        if kind not in SETTING_KINDS:
            return {"kind": kind, "target": "", "detail": _summary(op), "risky": False, "reason": None}
        key = op.get("key")
        extruder = op.get("extruder") if kind == "set_extruder_setting" else None
        try:
            facts = self._facts(key, extruder) or {}
        except Exception:
            facts = {}
        item = {"kind": kind, "target": key if extruder is None else "%s (e%s)" % (key, extruder),
                "before": facts.get("value"), "after": op.get("value"), "unit": facts.get("unit") or "",
                "limits": None, "risky": False, "reason": None}
        item["detail"] = "%s → %s%s" % ("?" if item["before"] is None else _shown(item["before"]), _shown(item["after"]),
                                        " " + item["unit"] if item["unit"] else "")
        reason, limits = self._risk(facts, op.get("value"))
        if reason is not None:
            item.update(risky=True, reason=reason, limits=limits)
        return item

    def _risk(self, facts, value):
        after = _number(value)
        if after is None:
            return None, None
        low, high = _number(facts.get("minimum_value")), _number(facts.get("maximum_value"))
        if (low is not None and after < low) or (high is not None and after > high):
            return "out_of_range", _limits(facts.get("minimum_value"), facts.get("maximum_value"))
        low, high = _number(facts.get("minimum_value_warning")), _number(facts.get("maximum_value_warning"))
        if (low is not None and after < low) or (high is not None and after > high):
            return "out_of_recommended", _limits(facts.get("minimum_value_warning"), facts.get("maximum_value_warning"))
        before = _number(facts.get("value"))
        ratio = self.ratio()
        if before is not None and before != 0 and after != 0 and (after / before > ratio or before / after > ratio
                                                                   or (after > 0) != (before > 0)):
            return "large_change", "×%s" % ("%g" % ratio)
        return None, None
