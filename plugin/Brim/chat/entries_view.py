import json
import os

from ..agent import ask_user
from ..agent.hub import LOCAL_SERVER
from ..agent.transcript import call_arguments, call_name, pending_question, rejection_comment
from ..protocol import constants
from . import markdown_html


def _payload(message):
    try:
        value = json.loads(message.get("content") or "")
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def _detail(name, message):
    payload = _payload(message) or {}
    status = message.get("brim_status")
    if status == "ok":
        if name == constants.TOOL_APPLY_CHANGES:
            return ", ".join(item.get("kind", "") for item in payload.get("applied") or []) or None
        return None
    error = payload.get("error")
    if status == "rejected":
        return rejection_comment((error or {}).get("message") if isinstance(error, dict) else None) or None
    if isinstance(error, dict):
        return "%s: %s" % (error.get("code"), error.get("message"))
    if status == "failed":
        return (message.get("content") or "")[:300]
    return None


def slice_result(message):
    payload = _payload(message) or {}
    result = payload.get("result") or {}
    files = result.get("files") or {}
    if not payload.get("ok") or not files:
        return None
    folder = os.path.dirname(next(iter(files.values())))
    return {"summary": result.get("slice") or {}, "files": files, "folder": folder}


def _question(call, results):
    answer = None
    reply = results.get(call.get("id"))
    if reply is not None:
        answer = (_payload(reply) or {}).get("answer")
    return {"kind": "question", "call_id": call.get("id"),
            "questions": ask_user.questions_of(call_arguments(call)), "answered": reply is not None, "answer": answer}


def _tool(call, results, running):
    name = call_name(call) or ""
    reply = results.get(call.get("id"))
    server = (reply or {}).get("brim_server") or (name.split("__")[0] if "__" in name else LOCAL_SERVER)
    status = (reply or {}).get("brim_status") or ("pending" if running else "skipped")
    if status == "running" and not running:
        status = "failed"
    label = name if server == LOCAL_SERVER else name[len(server) + 2:] if name.startswith(server + "__") else name
    return {"kind": "tool", "call_id": call.get("id"), "tool": label, "server": server, "status": status,
            "detail": _detail(label, reply) if reply is not None else None}


def build_entries(messages, running):
    results = dict((item.get("tool_call_id"), item) for item in messages if item.get("role") == "tool")
    entries = []
    for index, message in enumerate(messages):
        role = message.get("role")
        key = "m%d" % index
        if role == "user" and not message.get("brim_hidden"):
            entries.append({"kind": "user", "key": key, "text": message.get("content") or "",
                            "attachments": [item.get("name", "") for item in message.get("brim_attachments") or []]})
        elif role == "assistant":
            if message.get("content"):
                entries.append({"kind": "assistant", "key": key, "text": message["content"],
                                "html": markdown_html.render(message["content"]), "attachments": []})
            for position, call in enumerate(message.get("tool_calls") or []):
                entry = _question(call, results) if call_name(call) == ask_user.NAME else _tool(call, results, running)
                entry["key"] = "%s-%d" % (key, position)
                entries.append(entry)
                reply = results.get(call.get("id"))
                if entry["kind"] == "tool" and entry["server"] == LOCAL_SERVER and entry["tool"] == constants.TOOL_SLICE \
                        and reply is not None and reply.get("brim_status") == "ok":
                    result = slice_result(reply)
                    if result is not None:
                        entries.append({"kind": "result", "key": key + "-result", "result": result})
    return entries


def with_transient(entries, errors, confirmation):
    entries = list(entries)
    for position, error in enumerate(errors):
        entries.append(dict(error, key="e%d" % position))
    if confirmation is not None:
        entries.append(dict(confirmation, kind="confirmation", key="confirm-" + str(confirmation.get("call_id"))))
    return entries


def group_entries(entries):
    grouped = []
    run = []

    def flush():
        if len(run) >= 2:
            grouped.append({"kind": "tool_group", "key": "g" + run[0]["key"], "items": list(run)})
        else:
            grouped.extend(run)
        del run[:]

    for entry in entries:
        if entry["kind"] == "tool" and entry.get("status") == "ok":
            run.append(entry)
            continue
        flush()
        grouped.append(entry)
    flush()
    return grouped


def running_tool(entries):
    for entry in reversed(entries):
        if entry["kind"] == "tool" and entry.get("status") == "running":
            return entry["tool"]
    return None


def agent_status(snapshot, strings, llm_configured):
    if snapshot["switching"] is not None:
        return "busy", strings["status_%s_project" % snapshot["switching"]]
    if snapshot["workspace_blocked"]:
        return "error", strings["workspace_blocked"]
    if not llm_configured:
        return "muted", strings["llm_missing"]
    if snapshot["running"]:
        if snapshot["stopping"]:
            return "busy", strings["state_stopping"]
        if snapshot["confirmation"] is not None:
            return "attention", strings["state_awaiting_confirmation"]
        tool = running_tool(snapshot["entries"])
        if tool:
            return "busy", strings.get("tool_active_%s" % tool) or strings["state_executing_tool"]
        if snapshot.get("phase") == "thinking":
            return "busy", strings["activity_thinking"]
        return "busy", strings["state_agent_working"]
    if snapshot["question"] is not None:
        return "attention", strings["state_awaiting_user"]
    if snapshot["errors"]:
        return "error", strings["state_failed"]
    return "ok", strings["status_ready"]


def question_of(messages):
    return pending_question(messages)
