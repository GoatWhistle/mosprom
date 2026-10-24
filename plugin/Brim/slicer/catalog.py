from .material_catalog import inspect_material

MAX_MATCHES = 25
MAX_VALUES = 400


def _value(stack, key, prop="value"):
    try:
        item = stack.getProperty(key, prop)
    except Exception:
        return None
    if isinstance(item, (str, int, float, bool)) or item is None:
        return item
    return str(item)


class Catalog(object):
    def __init__(self, host, main):
        self._h = host
        self._main = main

    def search_settings(self, query):
        return self._main.call(self._search, query)

    def _search(self, query):
        stack = self._h.global_stack()
        words = [item for item in query.lower().split() if item]
        scored = []
        for definition in stack.definition.findDefinitions():
            text = " ".join([definition.key, str(definition.label), str(getattr(definition, "description", ""))]).lower()
            hits = sum(1 for word in words if word in text)
            if hits:
                exact = 2 if definition.key.lower() in words else 0
                scored.append((hits + exact, definition))
        scored.sort(key=lambda pair: (-pair[0], pair[1].key))
        matches = []
        for _, definition in scored[:MAX_MATCHES]:
            key = definition.key
            entry = {
                "key": key,
                "label": str(definition.label),
                "description": str(getattr(definition, "description", ""))[:300],
                "type": str(getattr(definition, "type", "")),
                "unit": str(getattr(definition, "unit", "") or ""),
                "value": _value(stack, key),
                "default_value": _value(stack, key, "default_value"),
                "minimum_value": _value(stack, key, "minimum_value"),
                "maximum_value": _value(stack, key, "maximum_value"),
                "settable_per_extruder": bool(getattr(definition, "settable_per_extruder", False)),
            }
            options = getattr(definition, "options", None)
            if options:
                entry["options"] = dict((str(k), str(v)) for k, v in options.items())
            matches.append(entry)
        return matches

    def inspect_profile(self):
        return self._main.call(self._profile)

    def _profile(self):
        manager = self._h.machine_manager()
        stack = manager.activeMachine
        quality = self._h.application.getQualityManager()
        groups = quality.getQualityGroups(stack)
        custom = quality.getQualityChangesGroups(stack)
        overrides = {}
        for item in [stack] + [stack.extruders[key] for key in sorted(stack.extruders.keys())]:
            for key in sorted(item.userChanges.getAllKeys())[:MAX_VALUES]:
                overrides["%s:%s" % (item.getId(), key)] = _value(item, key)
        return {
            "active_quality_type": manager.activeQualityType,
            "active_profile_name": manager.activeQualityOrQualityChangesName,
            "layer_height_mm": manager.activeQualityLayerHeight,
            "available_quality_types": sorted(key for key, group in groups.items() if group.is_available),
            "custom_profiles": sorted(custom.keys()),
            "user_overrides": overrides,
        }

    def inspect_material(self, material_id):
        return self._main.call(self._material, material_id)

    def _material(self, material_id):
        return inspect_material(self._h, material_id)
