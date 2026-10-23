from ..execution.errors import OperationError
from ..protocol import constants

MODE_KEY = "printing_mode"


class SettingsOperations(object):
    def __init__(self, host, main):
        self._h = host
        self._main = main

    def select_mode(self, op, guard=None):
        self._main.call(self._set_mode, op["mode"], guard=guard)
        return {"mode": op["mode"]}

    def _set_mode(self, mode):
        stack = self._h.global_stack()
        definition = stack.getSettingDefinition(MODE_KEY)
        if definition is None:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "this machine has no %s setting" % MODE_KEY)
        options = getattr(definition, "options", None) or {}
        if options and mode not in options:
            raise OperationError(constants.ERR_OPERATION_FAILED, "mode %s is not offered by this machine" % mode,
                                 {"available_modes": sorted(options.keys())})
        stack.userChanges.setProperty(MODE_KEY, "value", mode)

    def select_profile(self, op, guard=None):
        return self._main.call(self._set_profile, op["profile_id"], guard=guard)

    def _set_profile(self, profile_id):
        manager = self._h.machine_manager()
        stack = manager.activeMachine
        quality = self._h.application.getQualityManager()
        groups = quality.getQualityGroups(stack)
        if profile_id in groups and groups[profile_id].is_available:
            manager.setQualityGroupByQualityType(profile_id)
            return {"profile_id": profile_id, "kind": "quality_type"}
        custom = quality.getQualityChangesGroups(stack)
        if profile_id in custom:
            manager.setQualityChangesGroup(custom[profile_id])
            return {"profile_id": profile_id, "kind": "custom"}
        raise OperationError(constants.ERR_OPERATION_FAILED, "unknown profile %s" % profile_id, {
            "quality_types": sorted(key for key, group in groups.items() if group.is_available),
            "custom_profiles": sorted(custom.keys()),
        })

    def select_material(self, op, guard=None):
        return self._main.call(self._set_material, op["material_id"], op["extruder"], guard=guard)

    def _set_material(self, material_id, extruder):
        manager = self._h.machine_manager()
        stack = manager.activeMachine
        if str(extruder) not in stack.extruders:
            raise OperationError(constants.ERR_OPERATION_FAILED, "extruder %s does not exist" % extruder,
                                 {"extruders": sorted(stack.extruders.keys())})
        group = self._h.application.getMaterialManager().getMaterialGroup(material_id)
        if group is None:
            raise OperationError(constants.ERR_OPERATION_FAILED, "unknown material %s" % material_id)
        manager.setMaterialById(str(extruder), material_id)
        return {"material_id": material_id, "extruder": extruder}

    def set_global(self, op, guard=None):
        self._main.call(self._set_value, op["key"], op["value"], None, guard=guard)
        return {"key": op["key"], "value": op["value"]}

    def set_extruder(self, op, guard=None):
        self._main.call(self._set_value, op["key"], op["value"], op["extruder"], guard=guard)
        return {"key": op["key"], "value": op["value"], "extruder": op["extruder"]}

    def _set_value(self, key, value, extruder):
        stack = self._h.global_stack()
        definition = stack.getSettingDefinition(key)
        if definition is None:
            raise OperationError(constants.ERR_OPERATION_FAILED, "unknown setting %s" % key)
        if key == MODE_KEY:
            raise OperationError(constants.ERR_INVALID_ARGUMENTS, "use select_mode to change %s" % MODE_KEY)
        if extruder is not None:
            target = stack.extruders.get(str(extruder))
            if target is None:
                raise OperationError(constants.ERR_OPERATION_FAILED, "extruder %s does not exist" % extruder)
            target.userChanges.setProperty(key, "value", value)
            return
        stack.userChanges.setProperty(key, "value", value)
        if getattr(definition, "settable_per_extruder", False):
            for target in stack.extruders.values():
                target.userChanges.setProperty(key, "value", value)

    def reset_overrides(self, op, guard=None):
        keys = op.get("keys")
        return self._main.call(self._reset, keys, guard=guard)

    def _reset(self, keys):
        stack = self._h.global_stack()
        stacks = [stack] + list(stack.extruders.values())
        cleared = set()
        for item in stacks:
            names = set(item.userChanges.getAllKeys())
            for name in (names if keys is None else names.intersection(keys)):
                item.userChanges.removeInstance(name)
                cleared.add(name)
        return {"cleared": sorted(cleared)}

    def save_profile(self, op, guard=None):
        return self._main.call(self._save_profile, op["name"], guard=guard)

    def _save_profile(self, name):
        quality = self._h.application.getQualityManager()
        before = set(quality.getQualityChangesGroups(self._h.machine_manager().activeMachine).keys())
        quality.createQualityChanges(name)
        after = set(quality.getQualityChangesGroups(self._h.machine_manager().activeMachine).keys())
        created = sorted(after - before)
        if not created:
            raise OperationError(constants.ERR_OPERATION_FAILED, "the slicer did not create profile %s" % name)
        return {"profile_id": created[0]}
