from ..execution.errors import OperationError
from ..protocol import constants

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
        values = {}
        for key in sorted(stack.getAllKeys())[:MAX_VALUES]:
            values[key] = _value(stack, key)
        return {
            "active_quality_type": manager.activeQualityType,
            "active_profile_name": manager.activeQualityOrQualityChangesName,
            "layer_height_mm": manager.activeQualityLayerHeight,
            "available_quality_types": sorted(key for key, group in groups.items() if group.is_available),
            "custom_profiles": sorted(custom.keys()),
            "user_overrides": overrides,
            "values": values,
            "truncated": len(stack.getAllKeys()) > MAX_VALUES,
        }

    def inspect_material(self, material_id):
        return self._main.call(self._material, material_id)

    def _material(self, material_id):
        manager = self._h.machine_manager()
        stack = manager.activeMachine
        result = []
        for position in sorted(stack.extruders.keys()):
            extruder = stack.extruders[position]
            root = manager.currentRootMaterialId.get(position)
            if material_id and root != material_id:
                continue
            container = extruder.material
            metadata = container.getMetaData() if container is not None else {}
            facts = {}
            for key in ("name", "brand", "material", "color_name", "description", "adhesion_info",
                        "properties", "GUID", "diameter"):
                value = metadata.get(key)
                if isinstance(value, (str, int, float, bool, dict)):
                    facts[key] = value
            settings = {}
            if container is not None:
                for key in sorted(container.getAllKeys())[:80]:
                    settings[key] = _value(container, key)
            result.append({"extruder": int(position), "root_material_id": root, "facts": facts,
                           "material_settings": settings})
        if not result:
            raise OperationError(constants.ERR_OPERATION_FAILED, "material %s is not active on any extruder" % material_id)
        return {"materials": result}
