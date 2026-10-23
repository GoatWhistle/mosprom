def restore_runtime(state, runtime):
    state.run_id = runtime.get("run_id")
    state.run_state = None
    state.pending = None
    state.result = None
    state._slice_result = None
    state.progress = None
    state.entries = [entry for entry in state.entries if entry["kind"] in ("user", "assistant")]
    state._seen.clear()
    state._seen_order = []
    for event in runtime.get("events", []):
        if event.get("event") == "assistant_message":
            state._remember(event.get("event_id"))
        else:
            state.apply_chat_event(event)
    state.run_id = runtime.get("run_id")
    state.run_state = runtime.get("state")
    state.pending = runtime.get("pending")
    state.result = runtime.get("result")
    if state.run_state in ("completed", "aborted", "failed"):
        state.progress = None
    if state.pending is not None:
        kind = state.pending["type"]
        if not any(item["kind"] == kind for item in state.entries):
            item = dict(state.pending, kind=kind, run_id=state.run_id)
            if kind == "confirmation":
                item["decision"] = None
            state._push(item)


def conversation_row(item):
    return {"id": item["id"], "title": item.get("title") or "", "mode": item.get("mode", "ask"),
            "updated_at": str(item.get("updated_at", ""))}


class ChatHistory(object):
    def __init__(self, state, http, submit):
        self._state = state
        self._http = http
        self._submit = submit
        self._request = 0
        self._events = None

    def refresh(self, select_latest=False):
        def done(page):
            self._state.conversations = [conversation_row(item) for item in page.get("items", [])]
            if select_latest and self._state.conversation_id is None and self._state.conversations:
                self.open(self._state.conversations[0]["id"])
        self._submit(self._http.list_conversations, done)

    def open(self, conversation_id):
        if self._state.conversation_id != conversation_id:
            self._state.select_conversation(conversation_id, None)
        self.reload()

    def record(self, frame):
        if self._events is not None:
            self._events.append(frame)

    def reload(self):
        conversation_id = self._state.conversation_id
        if conversation_id is None:
            self.refresh(select_latest=True)
            return
        self._request += 1
        request = self._request
        self._events = []

        def done(detail):
            if request != self._request or conversation_id != self._state.conversation_id:
                return
            pending = self._events or []
            self._events = None
            self._state.load_history(detail)
            for frame in pending:
                self._state.apply_chat_event(frame)

        self._submit(lambda: self._http.get_conversation(conversation_id), done)
