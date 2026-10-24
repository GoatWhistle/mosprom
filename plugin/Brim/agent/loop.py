import json
import threading

from . import ask_user
from .conversation import read_file
from .llm_client import LlmError
from .transcript import call_name, dangling_calls, rejected_text, wire_messages

DEFAULT_MAX_STEPS = 40
WAIT_SLICE = 0.2
INTERRUPTED = json.dumps({"ok": False, "error": {"code": "interrupted", "message": (
    "the plugin stopped while this call was running; the outcome is unknown, re-read the scene")}})
IMAGES_NOTE = "Images returned by the previous tool calls."


def _error_result(code, message):
    return json.dumps({"ok": False, "error": {"code": code, "message": message}}, ensure_ascii=False)


def _skipped(call, answer):
    if call_name(call) == ask_user.NAME:
        if answer is not None:
            return ask_user.answer_result(answer), "ok"
        return _error_result("not_answered", "the user wrote a new message instead of answering"), "skipped"
    return _error_result("not_executed", "the turn stopped before this call ran; call it again if it is still needed"), "skipped"


class Turn(object):
    def __init__(self, loop, conversation, mode, emit, skill=None):
        self._loop = loop
        self.conversation = conversation
        self._mode = mode
        self._skill = skill or (lambda: None)
        self._emit = emit
        self._cancelled = threading.Event()
        self._released = threading.Event()
        self._decided = threading.Event()
        self._decision = None
        self._phase = "idle"
        self._thread = None

    def start(self, text=None, attachments=None, answer=None):
        self._thread = threading.Thread(target=self._run, args=(text, attachments or [], answer), daemon=True)
        self._thread.start()
        return self

    def join(self, timeout=None):
        if self._thread is not None:
            self._thread.join(timeout)

    def emit(self, kind, payload=None):
        if not self._released.is_set():
            self._emit(self, kind, payload or {})

    def cancelled(self):
        return self._cancelled.is_set()

    def cancel(self):
        self._cancelled.set()
        self._decided.set()
        if self._phase == "tool":
            self._loop.cancel_tools()
            return False
        self._released.set()
        return True

    def decide(self, decision, comment=""):
        self._decision = (decision, comment or "")
        self._decided.set()

    def _run(self, text, attachments, answer):
        try:
            self._turn(text, attachments, answer)
        except Exception as failure:
            self.emit("error", {"message": "%s: %s" % (type(failure).__name__, failure)})
        finally:
            self.emit("finished")
            self._released.set()

    def _turn(self, text, attachments, answer):
        conversation = self.conversation
        for call in dangling_calls(conversation.messages()):
            content, status = _skipped(call, answer)
            conversation.append({"role": "tool", "tool_call_id": call.get("id"), "content": content,
                                 "brim_tool": call_name(call), "brim_status": status})
        if text is not None or attachments:
            message = {"role": "user", "content": text or ""}
            if attachments:
                message["brim_attachments"] = attachments
                images = [{"path": item["path"], "mime_type": item["mime_type"]} for item in attachments
                          if item.get("kind") == "image"]
                if images:
                    message["brim_images"] = images
            conversation.append(message)
        conversation.save()
        self.emit("changed")
        for server, problem in self._loop.hub.refresh():
            self.emit("warning", {"server": server, "message": problem})
        for _ in range(self._loop.max_steps):
            if self.cancelled():
                return
            if not self._step():
                return
        self.emit("error", {"code": "step_limit", "message": "the agent reached the limit of %d steps" % self._loop.max_steps})

    def _step(self):
        conversation = self.conversation
        history = conversation.messages()
        tools = self._loop.hub.tools()
        messages = [self._loop.context.system_message(history, self._mode(), self._skill())] + wire_messages(history, read_file)
        self._phase = "llm"
        self.emit("thinking")
        try:
            reply = self._loop.llm.chat(messages, tools + [ask_user.DEFINITION])
        except LlmError as failure:
            if not self.cancelled():
                self.emit("error", {"code": "llm", "message": str(failure)})
            return False
        finally:
            self._phase = "idle"
        if self.cancelled():
            return False
        calls = reply["tool_calls"]
        message = {"role": "assistant", "content": reply["text"] or None}
        if calls:
            message["tool_calls"] = [{"id": call["id"], "type": "function", "function": {
                "name": call["name"],
                "arguments": call["raw_arguments"] if isinstance(call["raw_arguments"], str)
                else json.dumps(call["arguments"], ensure_ascii=False)}} for call in calls]
        elif not reply["text"]:
            message["content"] = ""
        conversation.append(message)
        conversation.save()
        self.emit("changed")
        if not calls:
            return False
        images = []
        for call in calls:
            if self.cancelled():
                return False
            if call["problem"]:
                self._record(call, _error_result("invalid_arguments", call["problem"]), "failed")
                continue
            if call["name"] == ask_user.NAME:
                if ask_user.questions_of(call["arguments"]):
                    conversation.save()
                    self.emit("question")
                    return False
                self._record(call, _error_result("invalid_arguments", "questions must be a non-empty list"), "failed")
                continue
            if not self._execute(call, images):
                return False
        if images:
            conversation.append({"role": "user", "content": IMAGES_NOTE, "brim_images": images, "brim_hidden": True})
        conversation.save()
        self.emit("changed")
        return True

    def _record(self, call, content, status, server=None, images=None):
        message = {"role": "tool", "tool_call_id": call["id"], "content": content, "brim_tool": call["name"],
                   "brim_status": status}
        if server:
            message["brim_server"] = server
        if images:
            message["brim_images"] = images
        return self.conversation.append(message)

    def _execute(self, call, images):
        described = self._loop.hub.describe(call["name"])
        if described is None:
            self._record(call, _error_result("unknown_tool", "no tool named %s" % call["name"]), "failed")
            return True
        tool = dict(described, name=call["name"])
        items = self._loop.policy.review(self._mode(), tool, call["arguments"])
        if items:
            decision, comment = self._confirm(call, tool, items)
            if decision is None:
                return False
            if decision != "accept":
                text = rejected_text(comment)
                self._record(call, _error_result("rejected_by_user", text), "rejected", tool["server"])
                self.conversation.save()
                self.emit("changed")
                return True
        index = self._record(call, INTERRUPTED, "running", tool["server"])
        self.conversation.save()
        self.emit("changed")
        self._phase = "tool"
        try:
            output = self._loop.hub.call(call["name"], call["arguments"])
        finally:
            self._phase = "idle"
        saved = [self.conversation.save_image(item["data"], item["mime_type"]) for item in output["images"]]
        images.extend(saved)
        message = {"role": "tool", "tool_call_id": call["id"], "content": output["text"] or "{}",
                   "brim_tool": call["name"], "brim_server": tool["server"],
                   "brim_status": "failed" if output["is_error"] else "ok"}
        if saved:
            message["brim_images"] = saved
        self.conversation.update(index, message)
        self.conversation.save()
        self.emit("changed")
        return not self.cancelled()

    def _confirm(self, call, tool, items):
        self._decided.clear()
        self._decision = None
        self._phase = "confirm"
        self.emit("confirm", {"call_id": call["id"], "tool": tool["name"], "server": tool["server"], "items": items})
        while not self._decided.wait(WAIT_SLICE):
            pass
        self._phase = "idle"
        if self.cancelled() or self._decision is None:
            return None, ""
        self.emit("confirmed", {"call_id": call["id"], "decision": self._decision[0]})
        return self._decision


class AgentLoop(object):
    def __init__(self, llm, hub, policy, context, cancel_tools, max_steps=DEFAULT_MAX_STEPS):
        self.llm = llm
        self.hub = hub
        self.policy = policy
        self.context = context
        self._cancel_tools = cancel_tools
        self.max_steps = max_steps

    def cancel_tools(self):
        self._cancel_tools()

    def turn(self, conversation, mode, emit, skill=None):
        return Turn(self, conversation, mode, emit, skill)
