from . import frames


class SceneAccess(object):
    def __init__(self, host):
        self._h = host
        self._counter = 0

    def objects(self):
        found = []
        for node in self._h.DepthFirstIterator(self._h.scene().getRoot()):
            if not isinstance(node, self._h.SceneNode):
                continue
            if not node.getMeshData() and not node.callDecoration("isGroup"):
                continue
            parent = node.getParent()
            if parent is not None and parent.callDecoration("isGroup"):
                continue
            if not node.callDecoration("isSliceable") and not node.callDecoration("isGroup"):
                continue
            found.append(node)
        return found

    def id_of(self, node):
        value = node.getSetting("brim_id", "")
        if not value:
            self._counter += 1
            value = "obj-%d" % self._counter
            while self.find(value) is not None:
                self._counter += 1
                value = "obj-%d" % self._counter
            node.setSetting("brim_id", value)
        return value

    def find(self, object_id):
        for node in self.objects():
            if node.getSetting("brim_id", "") == object_id:
                return node
        return None

    def require(self, object_id):
        node = self.find(object_id)
        if node is None:
            from ..execution.errors import OperationError
            from ..protocol import constants

            raise OperationError(constants.ERR_OPERATION_FAILED, "unknown object %s" % object_id,
                                 {"known_objects": [self.id_of(item) for item in self.objects()]})
        return node

    def bbox(self, node):
        box = node.getBoundingBox()
        low = frames.scene_to_build((box.left, box.bottom, box.back))
        high = frames.scene_to_build((box.right, box.top, box.front))
        mins = tuple(min(a, b) for a, b in zip(low, high))
        maxs = tuple(max(a, b) for a, b in zip(low, high))
        return mins, maxs

    def pivot(self, node, center):
        mins, maxs = self.bbox(node)
        if center == "origin":
            return frames.scene_to_build(tuple(node.getWorldPosition().getData()))
        middle = tuple((a + b) / 2.0 for a, b in zip(mins, maxs))
        if center == "bbox_bottom_center":
            return (middle[0], middle[1], mins[2])
        return middle

    def describe(self, node):
        mins, maxs = self.bbox(node)
        mesh = node.getMeshData()
        triangles = 0
        if mesh is not None and mesh.hasIndices():
            triangles = int(mesh.getFaceCount())
        elif mesh is not None:
            triangles = int(mesh.getVertexCount() // 3)
        q = node.getWorldOrientation()
        euler = frames.scene_quaternion_to_build_euler((q.x, q.y, q.z, q.w))
        scale = node.getWorldScale()
        return {
            "id": self.id_of(node),
            "name": node.getName(),
            "bbox_min_mm": [round(item, 3) for item in mins],
            "bbox_max_mm": [round(item, 3) for item in maxs],
            "size_mm": [round(b - a, 3) for a, b in zip(mins, maxs)],
            "center_mm": [round((a + b) / 2.0, 3) for a, b in zip(mins, maxs)],
            "rotation_deg": [round(item + 0.0, 3) for item in euler],
            "scale": [round(scale.x, 4), round(scale.z, 4), round(scale.y, 4)],
            "triangles": triangles,
            "extruder": self.extruder(node),
        }

    def extruder(self, node):
        position = node.callDecoration("getActiveExtruderPosition")
        try:
            return int(position)
        except (TypeError, ValueError):
            return 0
