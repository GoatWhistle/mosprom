SKIPPED_CATEGORIES = ("machine_settings", "command_line_settings")
FACT_PROPERTIES = ("value", "minimum_value", "maximum_value", "minimum_value_warning", "maximum_value_warning")
MAX_TEXT = 120
MAX_OPTIONS = 24


def _plain(value):
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, (int, str)):
        return value
    return str(value)


def _text(value):
    value = _plain(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    text = "null" if value is None else str(value)
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "..."


def _property(stack, key, name):
    try:
        return stack.getProperty(key, name)
    except Exception:
        return None


def _walk(definition):
    for child in getattr(definition, "children", None) or []:
        yield child
        for item in _walk(child):
            yield item


class SettingsDigest(object):
    def __init__(self, host):
        self._h = host
        self._cache = None

    def invalidate(self, *args):
        self._cache = None

    def read(self):
        if self._cache is None:
            self._cache = self._build()
        return self._cache

    def facts(self, key, extruder=None):
        stack = self._h.global_stack()
        if stack is None or not key:
            return None
        if extruder is not None:
            stack = stack.extruders.get(str(extruder), stack)
        definition = stack.getSettingDefinition(key) if hasattr(stack, "getSettingDefinition") else None
        facts = dict((name, _plain(_property(stack, key, name))) for name in FACT_PROPERTIES)
        facts["unit"] = str(getattr(definition, "unit", "") or "")
        facts["known"] = definition is not None or facts["value"] is not None
        return facts

    def _build(self):
        stack = self._h.global_stack()
        if stack is None:
            return []
        extruders = [(int(key), stack.extruders[key]) for key in sorted(stack.extruders.keys())
                     if getattr(stack.extruders[key], "isEnabled", True)]
        user_keys = set(stack.userChanges.getAllKeys())
        for _, extruder in extruders:
            user_keys.update(extruder.userChanges.getAllKeys())
        digest = []
        for category in stack.definition.definitions:
            if category.key in SKIPPED_CATEGORIES:
                continue
            lines = []
            for definition in _walk(category):
                if definition.type == "category" or not _property(stack, definition.key, "enabled"):
                    continue
                lines.append(self._line(stack, extruders, definition, definition.key in user_keys))
            if lines:
                digest.append({"category": category.key, "settings": lines})
        return digest

    def _line(self, stack, extruders, definition, overridden):
        key = definition.key
        value = _property(stack, key, "value")
        unit = str(getattr(definition, "unit", "") or "")
        details = [str(definition.type)]
        low = _property(stack, key, "minimum_value")
        high = _property(stack, key, "maximum_value")
        if low is not None or high is not None:
            details.append("%s..%s" % ("" if low is None else _text(low), "" if high is None else _text(high)))
        low = _property(stack, key, "minimum_value_warning")
        high = _property(stack, key, "maximum_value_warning")
        if low is not None or high is not None:
            details.append("recommended %s..%s" % ("" if low is None else _text(low), "" if high is None else _text(high)))
        options = getattr(definition, "options", None)
        if options:
            names = [str(item) for item in options.keys()]
            details.append("|".join(names[:MAX_OPTIONS]))
        if len(extruders) > 1 and getattr(definition, "settable_per_extruder", False):
            per_extruder = [(index, _property(extruder, key, "value")) for index, extruder in extruders]
            if any(_plain(item) != _plain(value) for _, item in per_extruder):
                details.append(", ".join("e%d=%s" % (index, _text(item)) for index, item in per_extruder))
        return "%s%s = %s%s (%s)" % ("*" if overridden else "", key, _text(value), " " + unit if unit else "",
                                     "; ".join(details))
