import json

from .prompts import SETTINGS_HEADER, SYSTEM_PROMPT


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
    def __init__(self, port, prompt=SYSTEM_PROMPT):
        self._port = port
        self._prompt = prompt

    def system_message(self, messages, mode):
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
        text = "%s\n\n[scene context, refreshed every request]\n%s%s" % (
            self._prompt, json.dumps(context, ensure_ascii=False), settings_text(settings))
        return {"role": "system", "content": text}
