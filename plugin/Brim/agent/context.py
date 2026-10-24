import json

from .prompts import PINNED_HEADER, SETTINGS_HEADER, SKILLS_HEADER, SYSTEM_PROMPT


def settings_text(settings):
    if not isinstance(settings, list):
        return ""
    lines = ["", SETTINGS_HEADER]
    for group in settings:
        if not isinstance(group, dict) or not isinstance(group.get("settings"), list):
            continue
        lines.append("## %s" % group.get("category"))
        lines.extend(str(item) for item in group["settings"])
    return "\n".join(lines)


def attachments_of(messages):
    seen = []
    for message in messages:
        for item in message.get("brim_attachments") or []:
            if item not in seen:
                seen.append(item)
    return seen


class SceneContext(object):
    def __init__(self, port, prompt=SYSTEM_PROMPT, skills=None):
        self._port = port
        self._prompt = prompt
        self._skills = skills

    def _skills_text(self, pinned):
        if self._skills is None or not self._skills.names():
            return ""
        text = "\n\n%s\n%s" % (SKILLS_HEADER, self._skills.catalog_text())
        body = self._skills.body(pinned) if pinned else None
        if body is not None:
            text += "\n\n%s %s\n%s" % (PINNED_HEADER, pinned, body)
        return text

    def system_message(self, messages, mode, skill=None):
        try:
            version, state = self._port.snapshot()
        except Exception as error:
            version, state = None, {"errors": ["scene unavailable: %s" % error]}
        state = dict(state)
        settings = state.pop("settings", None)
        context = {
            "confirmation_mode": mode,
            "scene_version": version,
            "scene_state": state,
            "attachments": [{"name": item.get("name"), "path": item.get("path"), "kind": item.get("kind")}
                            for item in attachments_of(messages)],
        }
        text = "%s%s\n\n[scene context, refreshed every request]\n%s%s" % (
            self._prompt, self._skills_text(skill), json.dumps(context, ensure_ascii=False), settings_text(settings))
        return {"role": "system", "content": text}
