from .history import conversation_row


class ChatMessaging(object):
    def __init__(self, state, http, settings, submit, notice, strings, bridge):
        self.state = state
        self._http = http
        self._settings = settings
        self._submit = submit
        self._notice = notice
        self._strings = strings
        self._bridge = bridge

    def send(self, text):
        text = (text or "").strip()
        pending = self.state.pending
        if pending is not None and pending["type"] == "confirmation":
            if text:
                self.confirm("clarify", text)
            else:
                self._notice(self._strings()["clarify_hint"])
            return
        if not text and not self.state.attachments:
            return
        if self.state.switching is not None or self.state.workspace_blocked:
            self._notice(self._strings()["workspace_blocked" if self.state.workspace_blocked else "switching"])
            return
        if self.state.run_active() and self.state.run_state != "awaiting_user" and (pending is None or pending["type"] != "question"):
            self._notice(self._strings()["busy_run"])
            return
        if not self._settings.llm_configured():
            self._notice(self._strings()["llm_missing"])
            return
        if self.state.conversation_id is None:
            self._create_then_send(text)
            return
        self._post_message(self.state.conversation_id, text)

    def _create_then_send(self, text):
        mode = self.state.mode

        def work():
            return self._http.create_conversation_with(mode)

        def done(created):
            kept = list(self.state.attachments)
            self.state.select_conversation(created["id"], created.get("mode"))
            self.state.attachments = kept
            self.state.conversations.insert(0, conversation_row(created))
            self._post_message(created["id"], text)

        self._submit(work, done, busy=True)

    def _post_message(self, conversation_id, text):
        attachments = list(self.state.attachments)
        ids = [item["id"] for item in attachments]
        mode = self.state.mode

        def work():
            return self._http.send_message(conversation_id, text, ids, mode)

        def done(reply):
            self.state.add_sent_message(reply.get("message_id"), reply.get("run_id"), text,
                                        [item["name"] for item in attachments])

        self._submit(work, done, busy=True)

    def confirm(self, decision, text=None):
        run_id = self.state.run_id
        pending = self.state.pending
        if run_id is None or pending is None or pending["type"] != "confirmation":
            return
        if decision == "clarify" and not (text or "").strip():
            self._notice(self._strings()["clarify_hint"])
            return

        def work():
            return self._http.confirm(run_id, decision, text)

        def done(_):
            if self.state.pending is not None and self.state.pending.get("batch_id") == pending.get("batch_id"):
                self.state.resolve_confirmation(decision)
                if decision == "clarify":
                    self.state.clear_draft()

        self._submit(work, done, busy=True)

    def stop(self):
        run_id = self.state.run_id
        if run_id is None or not self.state.run_active():
            return
        bridge = self._bridge()

        def work():
            reply = self._http.stop_run(run_id)
            return reply

        def done(_):
            self.state.mark_stopped()
            self.state.run_state = "aborted"
            if bridge is not None:
                bridge.cancel_run(run_id)

        self._submit(work, done, busy=True)

    def stop_then(self, proceed):
        run_id = self.state.run_id
        bridge = self._bridge()

        def work():
            self._http.stop_run(run_id)
            if bridge is not None:
                bridge.cancel_run(run_id)

        def done(_):
            self.state.mark_stopped()
            self.state.run_state = "aborted"
            proceed()

        self._submit(work, done, busy=True)
