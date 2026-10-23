import json

from ..execution.errors import OperationError
from ..protocol import constants

FACT_KEYS = ("name", "brand", "material", "color_name", "description", "adhesion_info",
             "properties", "GUID", "diameter")


def facts(metadata):
    return json.loads(json.dumps({key: metadata[key] for key in FACT_KEYS if key in metadata}, default=str))


def available_nodes(host):
    machine = host.machine_manager().activeMachine
    if machine is None:
        return []
    manager = host.application.getMaterialManager()
    result = []
    for position, extruder in sorted(machine.extruders.items()):
        available = manager.getAvailableMaterialsForMachineExtruder(machine, extruder) or {}
        for root_id, node in sorted(available.items()):
            result.append((int(position), root_id, node))
    return result


def available_materials(host):
    return [{"extruder": position, "material_id": root_id, "facts": facts(node.getMetadata())}
            for position, root_id, node in available_nodes(host)]


def inspect_material(host, material_id):
    machine = host.machine_manager()
    rows = []
    for position, root_id, node in available_nodes(host):
        if material_id is not None:
            if root_id != material_id:
                continue
        elif machine.currentRootMaterialId.get(str(position)) != root_id:
            continue
        container = node.getContainer()
        if container is None:
            raise OperationError(constants.ERR_NOT_AVAILABLE, "material profile could not be loaded")
        settings = {key: container.getProperty(key, "value") for key in sorted(container.getAllKeys())}
        rows.append({"extruder": position, "root_material_id": root_id,
                     "facts": facts(node.getMetadata()),
                     "material_settings": json.loads(json.dumps(settings, default=str))})
    if not rows:
        raise OperationError(constants.ERR_NOT_AVAILABLE, "material is unavailable for this machine")
    return {"materials": rows}
