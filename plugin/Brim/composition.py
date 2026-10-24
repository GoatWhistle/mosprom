import json
import os

from .agent.confirmation import ConfirmationPolicy
from .agent.context import SceneContext
from .agent.hub import McpHub
from .agent.llm_client import LlmClient
from .agent.loop import AgentLoop
from .agent.mcp_client import McpHttpClient
from .agent.skills import SkillCatalog
from .browser.bridge import WebBridge
from .browser.server import WebChatServer
from .knowledge.defects import DefectGuide
from .knowledge.materials import MaterialMatcher
from .chat.presenter import ChatPresenter
from .execution.executor import ToolExecutor
from .protocol.local_mcp import LocalMcpServer
from .protocol.mcp import McpDispatcher
from .protocol.tools import load_tools
from .settings import PluginSettings, PreferencesStore
from .slicer.catalog import Catalog
from .slicer.host import SlicerHost
from .slicer.main_thread import MainThread
from .slicer.nodes import SceneAccess
from .slicer.port import SlicerPort
from .slicer.render import Renderer
from .slicer.scene_ops import SceneOperations
from .slicer.settings_digest import SettingsDigest
from .slicer.settings_ops import SettingsOperations
from .slicer.slicing import SlicingService
from .slicer.state import StateReader
from .ui.controller import ChatController
from .workspace.service import WorkspaceService
from .workspace.store import WorkspaceStore

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


def preferences_of(application):
    getter = getattr(application, "getPreferences", None)
    if getter is not None:
        return getter()
    from UM.Preferences import Preferences

    return Preferences.getInstance()


class BrimRuntime(object):
    def __init__(self, application):
        self.application = application
        self.settings = PluginSettings(PreferencesStore(preferences_of(application)))
        self.host = SlicerHost()
        self.cache_dir = self.host.user_data_dir()
        os.makedirs(self.cache_dir, exist_ok=True)
        main = MainThread(application)
        access = SceneAccess(self.host)
        state = StateReader(self.host, access)
        self.port = SlicerPort(
            self.host, access, state, SceneOperations(self.host, access, main),
            SettingsOperations(self.host, main), Catalog(self.host, main),
            SlicingService(self.host, main, state), Renderer(self.host, main), main,
            SettingsDigest(self.host),
        )
        self.workspace = WorkspaceService(self.port, WorkspaceStore(os.path.join(self.cache_dir, "chats")))
        self.skills = SkillCatalog()
        self.executor = ToolExecutor(self.port, lambda: self.presenter.output_dir(), lambda: self.presenter.files_dir(),
                                     self.skills, DefectGuide(self.port.setting_facts),
                                     MaterialMatcher(self.port.read_state))
        self.dispatcher = McpDispatcher(load_tools(), self._execute)
        self.local_mcp = LocalMcpServer(self.dispatcher, port=self.settings.mcp_port())
        self.llm = LlmClient(self.settings.llm)
        self.hub = McpHub(self.dispatcher, self.settings.mcp_servers, lambda url, headers: McpHttpClient(url, headers))
        policy = ConfirmationPolicy(self.port.setting_facts, self.settings.risk_ratio)
        self.loop = AgentLoop(self.llm, self.hub, policy, SceneContext(self.port, skills=self.skills), self.executor.cancel)
        self.controller = ChatController(self._build_presenter, self.settings)
        self.port.add_change_listener(self._ui(lambda: self.presenter.on_scene_changed()))
        self.bridge = WebBridge(self.controller, self.cache_dir, os.path.join(self.cache_dir, "uploads"))
        self.web = WebChatServer(self.bridge, WEB_DIR)
        self._started = False

    @property
    def presenter(self):
        return self.controller.presenter

    def _execute(self, name, arguments):
        return self.executor.execute(name, arguments, self._ui(lambda stage, fraction:
                                                                  self.presenter.on_progress(stage, fraction)))

    def _build_presenter(self, runner, on_change):
        return ChatPresenter(self.settings, self.workspace, self.loop, self.llm, self.hub, runner, on_change,
                             post=lambda function: self.controller.post(function),
                             mcp_port=lambda: self.local_mcp.port(),
                             open_path=lambda path: self.controller.open_path(path), skills=self.skills)

    def _ui(self, handler):
        def deliver(*args):
            self.controller.post(lambda: handler(*args))

        return deliver

    def start(self):
        if self._started:
            return
        self._started = True
        self.port.watch()
        port = self.local_mcp.start()
        self.settings.set_mcp_port(port)
        self._write_mcp_info(port)
        self.controller.start()
        self.controller.add_view_listener(self.bridge.publish)
        self.web.start()

    def _write_mcp_info(self, port):
        path = os.path.join(self.cache_dir, "mcp.json")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump({"url": "http://127.0.0.1:%d/mcp" % port, "token": self.local_mcp.token()}, handle)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass

    def shutdown(self):
        if not self._started:
            return
        self._started = False
        try:
            self.presenter.flush_workspace()
        except Exception:
            pass
        self.local_mcp.stop()
        self.web.stop()
        self.controller.shutdown()
