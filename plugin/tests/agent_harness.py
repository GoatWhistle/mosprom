import json
import os
import tempfile
import threading

from tests import support
from tests.scripted_llm import ScriptedLlm, text_reply
from Brim.agent.confirmation import ConfirmationPolicy
from Brim.agent.context import SceneContext
from Brim.agent.conversation import Conversation
from Brim.agent.hub import McpHub
from Brim.agent.llm_client import LlmClient
from Brim.agent.loop import AgentLoop
from Brim.agent.mcp_client import McpHttpClient
from Brim.execution.executor import ToolExecutor
from Brim.protocol.mcp import McpDispatcher
from Brim.protocol.tools import load_tools


def calls_reply(*calls):
    return {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
        {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}
        for call_id, name, arguments in calls]}}]}


def call_reply(call_id, name, arguments):
    return calls_reply((call_id, name, arguments))


class Harness(object):
    def __init__(self, replies, servers=None, mode="ask", max_steps=40):
        self.directory = tempfile.mkdtemp()
        self.port = support.FakePort()
        self.executor = ToolExecutor(self.port, lambda: os.path.join(self.directory, "output"))
        os.makedirs(os.path.join(self.directory, "output"))
        self.llm_server = ScriptedLlm(replies)
        self.llm = LlmClient(lambda: {"base_url": "http://127.0.0.1:%d/v1" % self.llm_server.port,
                                      "model": "scripted", "api_key": "secret"}, timeout=10)
        self.servers = servers or []
        self.hub = McpHub(McpDispatcher(load_tools(), self.executor.execute), lambda: self.servers,
                          lambda url, headers: McpHttpClient(url, headers, timeout=5))
        self.loop = AgentLoop(self.llm, self.hub, ConfirmationPolicy(self.port.setting_facts, 2.0),
                              SceneContext(self.port), self.executor.cancel, max_steps=max_steps)
        self.mode = mode
        self.saved = []
        self.events = []
        self.decisions = []
        self.finished = threading.Event()
        self.conversation = self.new_conversation([])

    def new_conversation(self, messages):
        return Conversation("chat-1", messages, self.saved.append, os.path.join(self.directory, "files"))

    def emit(self, turn, kind, payload):
        self.events.append((kind, payload))
        if kind == "confirm":
            decision = self.decisions.pop(0) if self.decisions else ("accept", "")
            turn.decide(*decision)
        if kind == "finished":
            self.finished.set()

    def run(self, text=None, attachments=None, answer=None, conversation=None):
        self.finished.clear()
        self.events = []
        turn = self.loop.turn(conversation or self.conversation, lambda: self.mode, self.emit)
        turn.start(text=text, attachments=attachments, answer=answer)
        if not self.finished.wait(15):
            raise AssertionError("turn did not finish: %s" % self.events)
        turn.join(5)
        return turn

    def kinds(self):
        return [kind for kind, _ in self.events]

    def tool_messages(self):
        return [item for item in self.conversation.messages() if item["role"] == "tool"]

    def stop(self):
        self.llm_server.stop()


def done_reply(text="Готово"):
    return text_reply(text)
