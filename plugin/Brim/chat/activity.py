def running_tool_name(messages):
    for message in reversed(messages):
        if message.get("role") == "tool" and message.get("brim_status") == "running":
            return message.get("brim_tool") or ""
    return None


def activity_key(state):
    if not state.running:
        return None
    if state.stopping:
        return "stopping"
    if state.confirmation is not None:
        return "confirm"
    if state.progress is not None:
        return "slicing"
    tool = running_tool_name(state.messages)
    if tool is not None:
        return "tool:" + tool
    if state.phase == "thinking":
        return "thinking"
    return "working"


def activity_view(state, strings):
    key = state.activity
    if key is None or not state.running:
        return None
    kind, _, tool = key.partition(":")
    label = tool.split("__")[-1] if tool else ""
    if kind == "tool":
        text = strings.get("tool_active_%s" % label) or strings.get("tool_%s" % label) or label
    else:
        text = strings["activity_%s" % kind]
    return {"kind": kind, "since": state.activity_since, "step": state.step, "tool": label, "text": text}
