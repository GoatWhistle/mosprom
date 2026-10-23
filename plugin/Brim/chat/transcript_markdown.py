import json
import os

from ..agent import ask_user
from ..agent.transcript import call_arguments, call_name, rejection_comment
from ..protocol import constants

OPERATION_FIELDS = ("mode", "profile_id", "material_id", "key", "value", "extruder", "keys", "import_as",
                    "object_id", "object_ids", "frame", "position_mm", "rotation_deg", "rotation_center", "scale",
                    "count", "name")


def _payload(message):
    try:
        value = json.loads(message.get("content") or "")
    except (TypeError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _operation(operation, strings):
    kind = str(operation.get("kind") or "")
    parts = []
    for field in OPERATION_FIELDS:
        if field in operation:
            parts.append("%s=%s" % (field, _value(operation[field])))
    if operation.get("path"):
        parts.append("path=%s" % os.path.basename(str(operation["path"])))
    label = strings.get("op_" + kind) or kind
    return "%s (`%s`)%s" % (label, kind, ": " + ", ".join(parts) if parts else "")


def _duration(seconds):
    if seconds is None:
        return "—"
    return "%d:%02d" % (seconds // 3600, seconds % 3600 // 60)


def _slice_lines(payload, strings):
    result = payload.get("result") or {}
    summary = result.get("slice") or {}
    weights = ", ".join("%s g" % item for item in summary.get("material_weight_g") or [] if item)
    lines = ["  - %s: %s" % (strings["export_print_time"], _duration(summary.get("print_time_seconds")))]
    if weights:
        lines.append("  - %s: %s" % (strings["export_material"], weights))
    for name in sorted(result.get("files") or {}):
        lines.append("  - %s: `%s`" % (name, os.path.basename(result["files"][name])))
    return lines


def _question_lines(call, reply, strings):
    lines = ["", "**%s**" % strings["question"], ""]
    for question in ask_user.questions_of(call_arguments(call)):
        lines.append("- " + question["text"])
        for option in question["options"]:
            lines.append("  - " + option)
    if reply is not None:
        lines.extend(["", "**%s:** %s" % (strings["answered"], _payload(reply).get("answer") or "")])
    return lines


def _tool_lines(call, reply, strings):
    name = call_name(call) or ""
    arguments = call_arguments(call)
    status = (reply or {}).get("brim_status") or "skipped"
    label = strings.get("tool_" + name) or name
    lines = ["", "- **%s** (`%s`) — %s" % (label, name, strings.get("tool_" + status) or status)]
    if arguments.get("explanation"):
        lines.append("  > " + " ".join(str(arguments["explanation"]).split()))
    if name == constants.TOOL_APPLY_CHANGES:
        for operation in arguments.get("operations") or []:
            if isinstance(operation, dict):
                lines.append("  - " + _operation(operation, strings))
    elif arguments:
        lines.append("  - `%s`" % _value(arguments)[:400])
    payload = _payload(reply) if reply is not None else {}
    error = payload.get("error")
    if status == "rejected":
        comment = rejection_comment(error.get("message") if isinstance(error, dict) else None)
        lines.append("  - %s%s" % (strings["tool_rejected"], ": " + comment if comment else ""))
    elif isinstance(error, dict):
        lines.append("  - %s: `%s` %s" % (strings["error"], error.get("code"), error.get("message") or ""))
    if name == constants.TOOL_SLICE and status == "ok":
        lines.extend(_slice_lines(payload, strings))
    return lines


def render_markdown(chat, strings, model, exported_at):
    messages = chat.get("messages") or []
    results = dict((item.get("tool_call_id"), item) for item in messages if item.get("role") == "tool")
    lines = ["# " + (chat.get("title") or strings["new_chat"]), "",
             "%s: %s · %s: %s · %s: %s · %s: %s" % (
                 strings["export_created"], chat.get("created_at", "")[:16].replace("T", " "),
                 strings["mode"], strings.get("mode_" + str(chat.get("mode"))) or chat.get("mode"),
                 strings["export_model"], model or "—", strings["export_exported"], exported_at)]
    for message in messages:
        role = message.get("role")
        if role == "user" and not message.get("brim_hidden"):
            lines.extend(["", "## " + strings["you"], "", message.get("content") or ""])
            names = [item.get("name", "") for item in message.get("brim_attachments") or []]
            if names:
                lines.extend(["", "%s: %s" % (strings["files"], ", ".join("`%s`" % name for name in names))])
        elif role == "assistant":
            calls = message.get("tool_calls") or []
            if not message.get("content") and not calls:
                continue
            lines.extend(["", "## " + strings["agent"]])
            if message.get("content"):
                lines.extend(["", message["content"]])
            for call in calls:
                reply = results.get(call.get("id"))
                if call_name(call) == ask_user.NAME:
                    lines.extend(_question_lines(call, reply, strings))
                else:
                    lines.extend(_tool_lines(call, reply, strings))
    return "\n".join(lines) + "\n"
