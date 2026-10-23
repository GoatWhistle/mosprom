from dataclasses import dataclass

from app.usecase.artifacts import ArtifactService
from app.usecase.conversations import ConversationService
from app.usecase.instances import InstanceService
from app.usecase.interface.runtime import ConnectionRegistry
from app.usecase.plugin_session import PluginSession
from app.usecase.runs import RunService


@dataclass(frozen=True, slots=True)
class Services:
    instances: InstanceService
    conversations: ConversationService
    runs: RunService
    artifacts: ArtifactService
    session: PluginSession
    registry: ConnectionRegistry
