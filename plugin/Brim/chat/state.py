import time

MAX_ERRORS = 20


class ChatState(object):
    def __init__(self):
        self.conversations = []
        self.conversation_id = None
        self.mode = "ask"
        self.skill = None
        self.messages = []
        self.running = False
        self.stopping = False
        self.phase = None
        self.confirmation = None
        self.errors = []
        self.progress = None
        self.notice = None
        self.attachments = []
        self.busy = False
        self.exporting = False
        self.drafts = {}
        self.draft = ""
        self.draft_rev = 0
        self.switching = None
        self.switch_prompt = None
        self.switch_retry = None
        self.workspace_blocked = False
        self.save_state = None
        self.workspace_status = {}
        self.servers = {}
        self.step = 0
        self.activity = None
        self.activity_since = None

    def set_draft(self, text):
        self.draft = text or ""

    def clear_draft(self):
        self.draft = ""
        self.draft_rev += 1

    def select_conversation(self, conversation_id, mode, messages, skill=None):
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
        self.skill = skill or None
        self.messages = list(messages)
        self.confirmation = None
        self.errors = []
        self.progress = None
        self.phase = None
        self.reset_activity()

    def upsert_row(self, row):
        rows = [item for item in self.conversations if item["id"] != row["id"]]
        rows.insert(0, row)
        rows.sort(key=lambda item: item["updated_at"], reverse=True)
        self.conversations = rows

    def turn_started(self):
        self.running = True
        self.stopping = False
        self.phase = None
        self.confirmation = None
        self.errors = []
        self.progress = None
        self.attachments = []
        self.clear_draft()
        self.step = 0
        self.mark_activity("working")

    def turn_finished(self):
        self.running = False
        self.stopping = False
        self.phase = None
        self.confirmation = None
        self.progress = None
        self.reset_activity()

    def mark_activity(self, key):
        if key != self.activity:
            self.activity = key
            self.activity_since = time.time() if key is not None else None

    def reset_activity(self):
        self.step = 0
        self.mark_activity(None)

    def add_error(self, text):
        self.errors.append({"kind": "error", "text": text, "after": len(self.messages)})
        del self.errors[:-MAX_ERRORS]
