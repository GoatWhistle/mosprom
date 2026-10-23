from .material_catalog import available_materials

SLICE_STATES = {1: "not_started", 2: "processing", 3: "done", 4: "error", 5: "disabled"}
MAX_OVERRIDES = 60


def _plain(value):
    return value if isinstance(value, (str, int, float, bool)) or value is None else str(value)


def _safe(function, default, warnings, label):
    try:
        return function()
    except Exception as error:
        warnings.append("%s unavailable: %s" % (label, error))
        return default


class StateReader(object):
    def __init__(self, host, access):
        self._h = host
        self._access = access
        self.slice_state = "not_started"
        self.errors = []

    def read(self):
        manager = self._h.machine_manager()
        stack = manager.activeMachine
        if stack is None:
            return {"printer": None, "objects": [], "slice_state": self.slice_state, "errors": ["no printer"]}
        extruders = []
        roots = manager.currentRootMaterialId
        for position in sorted(stack.extruders.keys()):
            extruder = stack.extruders[position]
            extruders.append({
                "index": int(position),
                "enabled": bool(extruder.isEnabled),
                "material_id": roots.get(position),
                "variant": manager.activeVariantNames.get(position),
                "nozzle_mm": _plain(extruder.getProperty("machine_nozzle_size", "value")),
            })
        warnings = []
        quality = self._h.application.getQualityManager()
        groups = _safe(lambda: quality.getQualityGroups(stack), {}, warnings, "profiles")
        custom = _safe(lambda: sorted(quality.getQualityChangesGroups(stack).keys()), [], warnings, "custom profiles")
        overrides = {}
        for item in [stack] + [stack.extruders[key] for key in sorted(stack.extruders.keys())]:
            for key in sorted(item.userChanges.getAllKeys()):
                if len(overrides) < MAX_OVERRIDES:
                    overrides["%s:%s" % (item.getId(), key)] = _plain(item.getProperty(key, "value"))
        objects = _safe(lambda: [self._access.describe(node) for node in self._access.objects()], [], warnings, "objects")
        materials = _safe(lambda: available_materials(self._h), [], warnings, "materials")
        errors = list(self.errors) + warnings
        if _safe(lambda: manager.stacksHaveErrors, False, warnings, "validation"):
            errors.append("some settings have validation errors")
        return {
            "printer": {
                "name": manager.activeMachineName,
                "definition": manager.activeDefinitionId,
                "build_volume_mm": [
                    _plain(stack.getProperty("machine_width", "value")),
                    _plain(stack.getProperty("machine_depth", "value")),
                    _plain(stack.getProperty("machine_height", "value")),
                ],
                "extruders": extruders,
            },
            "mode": _plain(stack.getProperty("printing_mode", "value")),
            "profile": {
                "name": manager.activeQualityOrQualityChangesName,
                "quality_type": manager.activeQualityType,
                "layer_height_mm": manager.activeQualityLayerHeight,
            },
            "available_materials": materials,
            "available_profiles": sorted(key for key, group in groups.items() if group.is_available),
            "custom_profiles": custom,
            "overrides": overrides,
            "objects": objects,
            "slice_state": self.slice_state,
            "errors": errors,
        }

    def printer_summary(self):
        stack = self._h.machine_manager().activeMachine
        if stack is None:
            return {}
        modes = []
        definition = stack.getSettingDefinition("printing_mode")
        options = getattr(definition, "options", None) or {}
        modes = sorted(options.keys())
        return {"name": self._h.machine_manager().activeMachineName, "modes": modes}
