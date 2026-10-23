import itertools

from .history import restore_runtime

ACTIVE_STATES = ("interviewing", "agent_working", "awaiting_user", "awaiting_confirmation",
                 "executing_tool", "slicing", "saving")
WORKING_STATES = ("interviewing", "agent_working", "executing_tool", "slicing", "saving")
TERMINAL_STATES = ("completed", "failed", "aborted")
MAX_ENTRIES = 500
MAX_SEEN_EVENTS = 2000


class ChatState(object):
    def __init__(self):
        self._keys = itertools.count(1)
        self.conversations = []
        self.conversation_id = None
        self.mode = "ask"
        self.entries = []
        self.run_id = None
        self.run_state = None
        self.progress = None
        self.pending = None
        self.result = None
        self._slice_result = None
        self.connection = "disconnected"
        self.notice = None
        self.attachments = []
        self.busy = False
        self.drafts = {}
        self.draft = ""
        self.draft_rev = 0
        self.switching = None
        self.switch_prompt = None
        self.switch_retry = None
        self.workspace_blocked = False
        self.save_state = None
        self.workspace_status = {}
        self._seen = set()
        self._seen_order = []

    def _key(self):
        return "k%d" % next(self._keys)

    def _push(self, entry):
        entry["key"] = self._key()
        self.entries.append(entry)
        if len(self.entries) > MAX_ENTRIES:
            del self.entries[:len(self.entries) - MAX_ENTRIES]
        return entry

    def _remember(self, event_id):
        if event_id is None:
            return True
        if event_id in self._seen:
            return False
        self._seen.add(event_id)
        self._seen_order.append(event_id)
        while len(self._seen_order) > MAX_SEEN_EVENTS:
            self._seen.discard(self._seen_order.pop(0))
        return True

    def run_active(self):
        return self.run_state in ACTIVE_STATES

    def run_working(self):
        return self.run_state in WORKING_STATES

    def set_draft(self, text):
        self.draft = text or ""

    def clear_draft(self):
        self.draft = ""
        self.draft_rev += 1

    def select_conversation(self, conversation_id, mode):
        carried = None
        if self.conversation_id is None:
            carried = {"text": self.draft, "attachments": self.attachments}
        else:
            self.drafts[self.conversation_id] = {"text": self.draft, "attachments": self.attachments}
        stored = self.drafts.pop(conversation_id, None) or carried or {}
        self.draft = stored.get("text", "")
        self.attachments = list(stored.get("attachments", []))
        self.draft_rev += 1
        self.save_state = None
        self.conversation_id = conversation_id
        self.mode = mode or "ask"
        self.entries = []
        self.run_id = None
        self.run_state = None
        self.progress = None
        self.pending = None
        self.result = None
        self._slice_result = None
        self._seen = set()
        self._seen_order = []

    def load_history(self, detail):
        conversation = detail["conversation"]
        if conversation["id"] != self.conversation_id:
            return
        self.mode = conversation.get("mode", self.mode)
        history = []
        known_texts = set()
        for message in detail.get("messages", []):
            role = message["role"]
            if role not in ("user", "assistant"):
                continue
            history.append({"kind": role, "id": message["id"], "run_id": message.get("run_id"),
                            "text": message.get("content", ""), "attachments": message.get("attachment_ids", [])})
            if role == "assistant":
                known_texts.add((message.get("run_id"), message.get("content", "")))
        live = [item for item in self.entries if item["kind"] not in ("user", "assistant")
                or (item["kind"] == "assistant" and item.get("event_id") is not None
                    and (item.get("run_id"), item["text"]) not in known_texts)]
        self.entries = []
        for item in history:
            self._push(item)
        for item in live:
            self.entries.append(item)
        if "runtime" in detail:
            restore_runtime(self, detail["runtime"])

    def add_sent_message(self, message_id, run_id, text, attachment_names):
        self._push({"kind": "user", "id": message_id, "run_id": run_id, "text": text,
                    "attachments": list(attachment_names)})
        if self.run_id != run_id or self.run_state is None:
            self.run_id = run_id
            self.run_state = "interviewing"
            self.pending = None
        self.result = None
        self._slice_result = None
        self.progress = None
        self.attachments = []
        self.clear_draft()

    def apply_chat_event(self, frame):
        if frame.get("conversation_id") != self.conversation_id:
            return False
        if not self._remember(frame.get("event_id")):
            return False
        kind = frame.get("event")
        payload = frame.get("payload") or {}
        run_id = frame.get("run_id")
        if run_id and run_id != self.run_id:
            self.run_id = run_id
            self.result = None
            self._slice_result = None
            self.progress = None
        if kind == "assistant_message":
            self._push({"kind": "assistant", "event_id": frame.get("event_id"), "run_id": run_id,
                        "text": payload.get("text", ""), "attachments": []})
        elif kind == "question":
            self.pending = {"type": "question", "batch_id": payload.get("batch_id"),
                            "questions": list(payload.get("questions") or [])}
            self._push({"kind": "question", "run_id": run_id, "questions": self.pending["questions"]})
        elif kind == "confirmation_request":
            self.pending = {"type": "confirmation", "batch_id": payload.get("batch_id"),
                            "operations": list(payload.get("operations") or []),
                            "explanation": payload.get("explanation") or ""}
            self._push({"kind": "confirmation", "run_id": run_id, "batch_id": self.pending["batch_id"], "operations": self.pending["operations"],
                        "explanation": self.pending["explanation"], "decision": None})
        elif kind == "tool_started":
            self._push({"kind": "tool", "run_id": run_id, "call_id": payload.get("call_id"),
                        "tool": payload.get("tool"), "status": "running", "error": None, "detail": None})
        elif kind == "tool_finished":
            self._finish_tool(payload)
        elif kind == "run_state":
            self._set_run_state(payload.get("state"))
        elif kind == "error":
            self._push({"kind": "error", "run_id": run_id, "code": payload.get("code"),
                        "text": payload.get("message", "")})
            self._set_run_state("failed")
        return True

    def _set_run_state(self, state):
        self.run_state = state
        if state == "completed" and self._slice_result is not None:
            self.result = self._slice_result
        elif state in ("failed", "aborted", "agent_working"):
            self._slice_result = None
            self.result = None
        if state not in ("awaiting_user", "awaiting_confirmation"):
            self.pending = None
        if state in TERMINAL_STATES:
            self.progress = None

    def _finish_tool(self, payload):
        for entry in reversed(self.entries):
            if entry["kind"] == "tool" and entry.get("call_id") == payload.get("call_id"):
                entry["status"] = "ok" if payload.get("ok") else "failed"
                entry["error"] = payload.get("error")
                return
        self._push({"kind": "tool", "call_id": payload.get("call_id"), "tool": payload.get("tool"),
                    "status": "ok" if payload.get("ok") else "failed", "error": payload.get("error"), "detail": None})

    def apply_progress(self, frame):
        self.progress = {"stage": frame.get("stage"), "fraction": frame.get("fraction")}

    def apply_tool_result(self, frame, tool):
        if frame.get("run_id") != self.run_id:
            return
        for entry in reversed(self.entries):
            if entry["kind"] == "tool" and entry.get("call_id") == frame.get("call_id"):
                entry["detail"] = self._detail(tool, frame)
                break
        if tool == "slice" and frame.get("ok"):
            result = frame.get("result") or {}
            summary = result.get("slice") or {}
            self._slice_result = {"run_id": frame.get("run_id"), "summary": summary,
                           "artifacts": result.get("artifacts") or {}}
        self.progress = None

    def _detail(self, tool, frame):
        if frame.get("ok"):
            applied = frame.get("applied") or []
            if tool == "apply_changes":
                return ", ".join(item["kind"] for item in applied)
            return None
        error = frame.get("error") or {}
        return "%s: %s" % (error.get("code"), error.get("message"))

    def resolve_confirmation(self, decision):
        for entry in reversed(self.entries):
            if entry["kind"] == "confirmation" and entry["decision"] is None:
                entry["decision"] = decision
                break
        self.pending = None

    def mark_stopped(self):
        self.pending = None
        self.progress = None
