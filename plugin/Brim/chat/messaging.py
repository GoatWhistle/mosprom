from ..agent.transcript import call_arguments
from .activity import activity_key
from .entries_view import question_of
from .files import copy_into


class ChatMessaging(object):
    def __init__(self, state, settings, loop, conversation, submit, post, notice, strings, changed):
        self.state = state
        self._settings = settings
        self._loop = loop
        self._conversation = conversation
        self._submit = submit
        self._post = post
        self._notice = notice
        self._strings = strings
        self._changed = changed
        self._turn = None
        self._after_turn = []

    def send(self, text, ensure_conversation):
        state = self.state
        text = (text or "").strip()
        if state.confirmation is not None:
            self._notice(self._strings()["confirm_first"])
            return
        if not text and not state.attachments:
            return
        if state.switching is not None or state.workspace_blocked:
            self._notice(self._strings()["workspace_blocked" if state.workspace_blocked else "switching"])
            return
        if state.running or self._turn is not None:
            self._notice(self._strings()["busy_run"])
            return
        if not self._settings.llm_configured():
            self._notice(self._strings()["llm_missing"])
            return
        if state.conversation_id is None:
            ensure_conversation(lambda: self._begin(text))
            return
        self._begin(text)

    def _begin(self, text):
        state = self.state
        conversation = self._conversation()
        if conversation is None:
            return
        attachments = list(state.attachments)
        question = question_of(state.messages)
        answer = text if question is not None else None
        directory = conversation.files_dir

        def work():
            return copy_into(attachments, directory) if attachments else []

        def done(copied):
            if self._conversation() is not conversation or state.running:
                return
            self._start(conversation, None if answer is not None else text, copied, answer)

        state.busy = True
        self._submit(work, done, on_error=self._copy_failed)

    def _copy_failed(self, error):
        self.state.busy = False
        self._notice("%s: %s" % (self._strings()["attach_failed"], error))

    def _start(self, conversation, text, attachments, answer):
        state = self.state
        state.busy = False
        state.turn_started()
        conversation_id = conversation.id
        turn = self._loop.turn(conversation, lambda: self.state.mode if self.state.conversation_id == conversation_id
                               else "ask", self._deliver,
                               lambda: self.state.skill if self.state.conversation_id == conversation_id else None)
        self._turn = turn
        turn.start(text=text, attachments=attachments, answer=answer)

    def _deliver(self, turn, kind, payload):
        self._post(lambda: self._on_event(turn, kind, payload))

    def _on_event(self, turn, kind, payload):
        if turn is not self._turn:
            return
        state = self.state
        if kind == "finished":
            self._finish_turn()
            return
        if kind == "thinking":
            state.phase = "thinking"
            state.progress = None
            state.step += 1
        elif kind == "confirm":
            state.confirmation = dict(payload, explanation=self._explanation(turn, payload))
        elif kind == "confirmed":
            state.confirmation = None
        elif kind == "warning":
            self._notice("MCP %s: %s" % (payload.get("server"), payload.get("message")))
        elif kind == "error":
            state.add_error(payload.get("message", ""))
        state.messages = turn.conversation.messages()
        state.mark_activity(activity_key(state))
        self._changed()

    def _explanation(self, turn, payload):
        for message in reversed(turn.conversation.messages()):
            for call in message.get("tool_calls") or []:
                if call.get("id") == payload.get("call_id"):
                    return str(call_arguments(call).get("explanation") or message.get("content") or "")
        return ""

    def _finish_turn(self):
        turn, self._turn = self._turn, None
        if turn is not None:
            self.state.messages = turn.conversation.messages()
        self.state.turn_finished()
        waiting, self._after_turn = self._after_turn, []
        for proceed in waiting:
            proceed()
        self._changed()

    def on_progress(self, stage, fraction):
        if self._turn is not None:
            self.state.progress = {"stage": stage, "fraction": fraction}
            self.state.mark_activity(activity_key(self.state))
            self._changed()

    def confirm(self, decision, comment=None):
        if self._turn is None or self.state.confirmation is None:
            return
        self._turn.decide(decision, (comment or "").strip())
        self.state.confirmation = None
        if (comment or "").strip():
            self.state.clear_draft()
        self.state.mark_activity(activity_key(self.state))
        self._changed()

    def stop(self):
        self.stop_then(None)

    def when_idle(self, proceed):
        if self._turn is None:
            proceed()
        else:
            self._after_turn.append(proceed)

    def stop_then(self, proceed):
        turn = self._turn
        if turn is None:
            if proceed is not None:
                proceed()
            return
        if proceed is not None:
            self._after_turn.append(proceed)
        self.state.stopping = True
        self.state.confirmation = None
        self.state.mark_activity(activity_key(self.state))
        if turn.cancel():
            self._finish_turn()
        else:
            self._changed()

    def busy(self):
        return self._turn is not None
