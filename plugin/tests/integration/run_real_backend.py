import hashlib
import os
import queue
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from tests import support
from tests.integration.scripted_llm import ScriptedLlm, text_reply, tool_reply
from Brim.chat.presenter import ChatPresenter
from Brim.execution.artifacts import ArtifactService
from Brim.execution.attachments import AttachmentCache
from Brim.execution.executor import ToolExecutor
from Brim.execution.ledger import CallLedger
from Brim.protocol import frames
from Brim.protocol.authorization import AuthorizedCalls
from Brim.protocol.backend_http import BackendHttpClient
from Brim.protocol.bridge import BridgeConnection
from Brim.protocol.mcp import McpDispatcher
from Brim.protocol.tools import load_tools
from Brim.settings import MemoryStore, PluginSettings, RegisteredConnection
from Brim.ui.runner import ImmediateRunner

BACKEND = os.environ.get("BRIM_BACKEND", "http://localhost:8000")
LLM_HOST = os.environ.get("BRIM_LLM_HOST", "host.docker.internal")


def wait_until(predicate, label, timeout=60.0):
    end = time.time() + timeout
    while time.time() < end:
        if predicate():
            return
        time.sleep(0.1)
    raise SystemExit("timeout waiting for: %s" % label)


def main():
    work = tempfile.mkdtemp()
    stl = os.path.join(work, "bracket.stl")
    with open(stl, "wb") as handle:
        handle.write(b"solid bracket\nendsolid bracket\n")
    attachment = {}

    def apply_reply():
        return tool_reply("c1", "apply_changes", {"explanation": "PETG, import the bracket", "operations": [
            {"kind": "select_mode", "mode": "classic"},
            {"kind": "select_material", "material_id": "petg", "extruder": 0},
            {"kind": "import_model", "attachment_id": attachment["id"], "name": "bracket.stl"},
        ]})

    llm = ScriptedLlm([
        tool_reply("q1", "ask_user", {"questions": [{"text": "Which material and load?"}]}),
        tool_reply("r1", "ask_user", {"questions": [], "requirements_summary": "PETG bracket, no supports"}),
        apply_reply,
        tool_reply("s1", "slice", {}),
        text_reply("Done: PETG, classic mode, bracket imported and sliced."),
    ])
    settings = PluginSettings(MemoryStore({
        "backend_url": BACKEND, "llm_base_url": "http://%s:%d/v1" % (LLM_HOST, llm.port),
        "llm_model": "scripted", "llm_api_key": "not-a-real-key"}))
    connection = RegisteredConnection(settings)
    http = BackendHttpClient(connection)
    connection.bind(http)
    port = support.FakePort()
    ledger = CallLedger(os.path.join(work, "ledger.json"))
    executor = ToolExecutor(port, ledger, AttachmentCache(http, work), ArtifactService(http, os.path.join(work, "art")))
    trusted = McpDispatcher(load_tools(), lambda n, a, r, m: executor.execute_mcp(n, a, r))
    inbox = queue.Queue()
    results = []
    bridge = BridgeConnection(
        connection, lambda: frames.hello_frame(settings.instance_id(), "7.10-fake", ["classic", "cylindrical", "cylindrical_full"], port.printer_summary()),
        ledger, executor, trusted, lambda: (port.scene_version(), port.read_state()),
        on_chat_event=lambda f: inbox.put(("chat", f)), on_status=lambda s: inbox.put(("status", s)),
        on_progress=lambda f: inbox.put(("progress", f)), on_tool_result=lambda f, t: inbox.put(("result", (f, t))),
        authorized=AuthorizedCalls())
    presenter = ChatPresenter(http, settings, ImmediateRunner(), lambda: None, bridge=bridge)

    def pump():
        while True:
            try:
                kind, value = inbox.get_nowait()
            except queue.Empty:
                return
            if kind == "chat":
                presenter.on_chat_event(value)
            elif kind == "status":
                presenter.on_status(value)
            elif kind == "progress":
                presenter.on_progress(value)
            else:
                presenter.on_tool_result(*value)
                results.append((value[1], value[0]["ok"], (value[0].get("error") or {}).get("code")))

    def until(predicate, label, timeout=60.0):
        end = time.time() + timeout
        while time.time() < end:
            pump()
            if predicate():
                return
            time.sleep(0.1)
        run = http.get_run(presenter.state.run_id) if presenter.state.run_id else None
        raise SystemExit("timeout waiting for: %s; presenter=%s notice=%s results=%s llm_requests=%d backend_run=%s" % (
            label, presenter.state.run_state, presenter.state.notice, results, len(llm.requests), run))

    bridge.start()
    presenter.start()
    until(lambda: presenter.state.connection == "connected", "websocket connected")
    print("1. registered and connected; token stored:", bool(settings.token()))
    presenter.new_conversation()
    until(lambda: presenter.state.conversation_id, "conversation created")
    presenter.attach(stl)
    until(lambda: presenter.state.attachments, "attachment uploaded")
    attachment["id"] = presenter.state.attachments[0]["id"]
    print("2. attachment uploaded:", attachment["id"], "scene objects untouched:", port.applied == [])
    presenter.send("Load-bearing bracket, PETG, no supports")
    until(lambda: presenter.state.pending and presenter.state.pending["type"] == "question", "agent question")
    print("3. agent question:", presenter.state.pending["questions"])
    until(lambda: presenter.state.run_state == "awaiting_user", "awaiting_user")
    presenter.send("PETG, holds about 5 kg")
    until(lambda: presenter.state.pending and presenter.state.pending["type"] == "confirmation", "confirmation request")
    ops = [item["kind"] for item in presenter.state.pending["operations"]]
    print("4. confirmation card operations:", ops, "| scene still untouched:", port.applied == [])
    assert port.applied == [], "scene changed before confirmation"
    presenter.confirm("accept")
    until(lambda: presenter.state.run_state == "completed", "run completed", timeout=90.0)
    print("5. run completed; plugin tool results:", results)
    print("   applied operations:", [item["kind"] for item in port.applied])
    run_id = presenter.state.run_id
    listing = http.list_artifacts(run_id)
    for kind in ("gcode", "3mf"):
        payload, _ = http.download_artifact(run_id, kind)
        local = os.path.join(work, "art", "result.gcode" if kind == "gcode" else "result.3mf")
        with open(local, "rb") as handle:
            sent = handle.read()
        assert payload == sent, kind
        print("6. %s stored on backend: %d bytes, sha256 matches local: %s" % (kind, len(payload), hashlib.sha256(payload).hexdigest() == hashlib.sha256(sent).hexdigest()))
    print("   artifacts listed:", sorted(item["kind"] for item in listing))
    assert sorted(item["kind"] for item in listing) == ["3mf", "gcode"]
    detail = http.get_conversation(presenter.state.conversation_id)
    print("7. history on backend:", [(m["role"], m["content"][:40]) for m in detail["messages"]])
    presenter.reload_history()
    users = [e for e in presenter.state.entries if e["kind"] == "user"]
    assistants = [e for e in presenter.state.entries if e["kind"] == "assistant"]
    print("8. after reload: user messages %d, assistant messages %d" % (len(users), len(assistants)))
    assert len(users) == 2 and len(assistants) >= 1
    print("   LLM requests served:", len(llm.requests), "| key never in conversation:", "not-a-real-key" not in str(detail))
    bridge.stop()
    llm.stop()
    print("OK")


if __name__ == "__main__":
    main()
