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


def with_result(entries, result):
    if result is None:
        return entries
    return entries + [{"kind": "result", "key": "result", "result": result}]


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
    if snapshot["connection"] != "connected":
        return "error", strings["status_offline"]
    if not llm_configured:
        return "muted", strings["llm_missing"]
    state = snapshot["run_state"]
    if snapshot["run_active"]:
        tool = running_tool(snapshot["entries"]) if state == "executing_tool" else None
        text = strings.get("tool_active_%s" % tool) if tool else None
        kind = "busy" if state in ("interviewing", "agent_working", "executing_tool", "slicing", "saving") else "attention"
        return kind, text or strings.get("state_%s" % state, "")
    if state in ("failed", "aborted"):
        return "error" if state == "failed" else "muted", strings["state_%s" % state]
    return "ok", strings["status_ready"]
