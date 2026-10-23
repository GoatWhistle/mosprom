MAX_ERRORS = 20


class ChatState(object):
    def __init__(self):
        self.conversations = []
        self.conversation_id = None
        self.mode = "ask"
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

    def set_draft(self, text):
        self.draft = text or ""

    def clear_draft(self):
        self.draft = ""
        self.draft_rev += 1

    def select_conversation(self, conversation_id, mode, messages):
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
        self.messages = list(messages)
        self.confirmation = None
        self.errors = []
        self.progress = None
        self.phase = None

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

    def turn_finished(self):
        self.running = False
        self.stopping = False
        self.phase = None
        self.confirmation = None
        self.progress = None

    def add_error(self, text):
        self.errors.append({"kind": "error", "text": text, "after": len(self.messages)})
        del self.errors[:-MAX_ERRORS]
