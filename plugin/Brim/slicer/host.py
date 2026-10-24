import os

from PyQt5.QtCore import QBuffer, QIODevice, QUrl
from UM.Application import Application
from UM.Math.Quaternion import Quaternion
from UM.Math.Vector import Vector
from UM.Operations.AddSceneNodeOperation import AddSceneNodeOperation
from UM.Operations.GroupedOperation import GroupedOperation
from UM.Operations.RemoveSceneNodeOperation import RemoveSceneNodeOperation
from UM.Operations.SetTransformOperation import SetTransformOperation
from UM.Operations.TranslateOperation import TranslateOperation
from UM.PluginRegistry import PluginRegistry
from UM.Scene.Iterator.DepthFirstIterator import DepthFirstIterator
from UM.Scene.SceneNode import SceneNode
from UM.Scene.Selection import Selection
from UM.Backend.Backend import BackendState

from steslicer.Arranging.ArrangeObjectsJob import ArrangeObjectsJob
from steslicer.MultiplyObjectsJob import MultiplyObjectsJob
from steslicer.Snapshot import Snapshot


class SlicerHost(object):
    QBuffer = QBuffer
    QIODevice = QIODevice
    QUrl = QUrl
    Quaternion = Quaternion
    Vector = Vector
    AddSceneNodeOperation = AddSceneNodeOperation
    GroupedOperation = GroupedOperation
    RemoveSceneNodeOperation = RemoveSceneNodeOperation
    SetTransformOperation = SetTransformOperation
    TranslateOperation = TranslateOperation
    DepthFirstIterator = DepthFirstIterator
    SceneNode = SceneNode
    Selection = Selection
    BackendState = BackendState
    ArrangeObjectsJob = ArrangeObjectsJob
    MultiplyObjectsJob = MultiplyObjectsJob
    Snapshot = Snapshot

    def __init__(self):
        self.application = Application.getInstance()

    def plugin(self, plugin_id):
        return PluginRegistry.getInstance().getPluginObject(plugin_id)

    def scene(self):
        return self.application.getController().getScene()

    def machine_manager(self):
        return self.application.getMachineManager()

    def global_stack(self):
        return self.application.getGlobalContainerStack()

    def backend(self):
        return self.application.getBackend()

    def plugin_path(self, plugin_id):
        return PluginRegistry.getInstance().getPluginPath(plugin_id)

    def log_path(self):
        from UM.Resources import Resources

        return os.path.join(Resources.getDataStoragePath(), "steslicer.log")

    def user_data_dir(self):
        from UM.Resources import Resources

        return os.path.join(Resources.getDataStoragePath(), "brim")
