import json
import os

from .chat.presenter import ChatPresenter
from .execution.artifacts import ArtifactService
from .execution.attachments import AttachmentCache
from .execution.executor import ToolExecutor
from .execution.ledger import CallLedger
from .protocol import constants, frames
from .protocol.authorization import AuthorizedCalls, McpAuthorizationGate
from .protocol.backend_http import BackendHttpClient
from .protocol.bridge import BridgeConnection
from .protocol.local_mcp import LocalMcpServer
from .protocol.mcp import McpDispatcher
from .protocol.tools import load_tools
from .settings import PluginSettings, PreferencesStore, RegisteredConnection
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


def preferences_of(application):
    getter = getattr(application, "getPreferences", None)
    if getter is not None:
        return getter()
    from UM.Preferences import Preferences

    return Preferences.getInstance()


def plugin_tools():
    return [tool for tool in load_tools() if tool["name"] != constants.TOOL_ASK_USER]


class BrimRuntime(object):
    def __init__(self, application):
        self.application = application
        self.settings = PluginSettings(PreferencesStore(preferences_of(application)))
        self.host = SlicerHost()
        self.cache_dir = self.host.user_data_dir()
        os.makedirs(self.cache_dir, exist_ok=True)
        connection = RegisteredConnection(self.settings)
        self.http = BackendHttpClient(connection)
        connection.bind(self.http)
        main = MainThread(application)
        access = SceneAccess(self.host)
        state = StateReader(self.host, access)
        self.port = SlicerPort(
            self.host, access, state, SceneOperations(self.host, access, main),
            SettingsOperations(self.host, main), Catalog(self.host, main),
            SlicingService(self.host, main, state), Renderer(self.host, main, self.http), main,
            SettingsDigest(self.host),
        )
        self.ledger = CallLedger(os.path.join(self.cache_dir, "ledger.json"))
        attachments = AttachmentCache(self.http, self.cache_dir)
        artifacts = ArtifactService(self.http, os.path.join(self.cache_dir, "artifacts"))
        self.executor = ToolExecutor(self.port, self.ledger, attachments, artifacts)
        self.authorized = AuthorizedCalls()
        tools = plugin_tools()
        trusted = McpDispatcher(tools, lambda name, arguments, request_id, meta:
                                self.executor.execute_mcp(name, arguments, request_id))
        gate = McpAuthorizationGate(self.executor, self.authorized)
        self.local_mcp = LocalMcpServer(McpDispatcher(tools, gate.handle), port=self.settings.mcp_port())
        self.workspace = WorkspaceService(self.port, WorkspaceStore(os.path.join(self.cache_dir, "workspaces")))
        self.controller = ChatController(self._build_presenter)
        self.bridge = BridgeConnection(
            connection, self._hello, self.ledger, self.executor, trusted, self._snapshot,
            on_chat_event=self._ui(lambda frame: self.presenter.on_chat_event(frame)),
            on_status=self._ui(lambda status: self.presenter.on_status(status)),
            on_progress=self._ui(lambda frame: self.presenter.on_progress(frame)),
            on_tool_result=self._ui(lambda frame, tool: self.presenter.on_tool_result(frame, tool)),
            authorized=self.authorized,
        )
        self.presenter.attach_bridge(self.bridge)
        self.port.add_change_listener(self.bridge.schedule_snapshot)
        self.port.add_change_listener(self._ui(lambda: self.presenter.on_scene_changed()))
        self._started = False

    @property
    def presenter(self):
        return self.controller.presenter

    def _build_presenter(self, runner, on_change):
        return ChatPresenter(self.http, self.settings, runner, on_change,
                             mcp_port=lambda: self.local_mcp.port(), cache_dir=self.cache_dir,
                             workspace=self.workspace, post=lambda function: self.controller.post(function))

    def _ui(self, handler):
        def deliver(*args):
            self.controller.post(lambda: handler(*args))

        return deliver

    def _slicer_version(self):
        getter = getattr(self.application, "getVersion", None)
        try:
            return str(getter()) if getter is not None else "unknown"
        except Exception:
            return "unknown"

    def _hello(self):
        printer = self.port.printer_summary()
        modes = [mode for mode in printer.get("modes", []) if mode in constants.PRINT_MODES] or list(constants.PRINT_MODES)
        return frames.hello_frame(self.settings.instance_id(), self._slicer_version(), modes, printer, self.port.scene_epoch())

    def _snapshot(self):
        return self.port.snapshot()

    def start(self):
        if self._started:
            return
        self._started = True
        self.port.watch()
        port = self.local_mcp.start()
        self.settings.set_mcp_port(port)
        self._write_mcp_info(port)
        self.bridge.start()
        self.controller.start()

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
        self.bridge.stop()
        self.local_mcp.stop()
        self.controller.shutdown()
