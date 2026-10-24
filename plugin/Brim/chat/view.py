from ..agent.hub import LOCAL_SERVER
from ..ui.strings import strings_for
from .activity import activity_view
from .entries_view import agent_status, build_entries, group_entries, question_of, with_transient


def _servers(settings, status):
    rows = [dict({"name": LOCAL_SERVER, "url": "", "enabled": True, "pinned": True},
                 **(status.get(LOCAL_SERVER) or {"state": "unknown", "tools": 0, "error": None}))]
    for server in settings.mcp_servers():
        known = status.get(server["name"]) or {"state": "off" if not server["enabled"] else "unknown",
                                               "tools": 0, "error": None}
        rows.append(dict({"name": server["name"], "url": server["url"], "enabled": server["enabled"], "pinned": False},
                         **known))
    return rows


def chat_view(state, settings, mcp_port, notice, skills=()):
    strings = strings_for(settings.language())
    entries = build_entries(state.messages, state.running)
    question = None if state.running else question_of(state.messages)
    snapshot = {
        "conversations": list(state.conversations),
        "conversation_id": state.conversation_id,
        "mode": state.mode,
        "skill": state.skill or "",
        "skill_options": ([{"name": "", "title": strings["skill_auto"]}] if skills else [])
        + [{"name": item.get("name"), "title": item.get("title_" + settings.language()) or item.get("name")}
           for item in skills],
        "entries": entries,
        "running": state.running,
        "stopping": state.stopping,
        "confirmation": state.confirmation,
        "question": question,
        "errors": list(state.errors),
        "progress": state.progress,
        "notice": state.notice,
        "attachments": list(state.attachments),
        "busy": state.busy,
        "exporting": state.exporting,
        "draft": state.draft,
        "draft_rev": state.draft_rev,
        "switching": state.switching,
        "switch_prompt": state.switch_prompt is not None,
        "can_retry_switch": state.switch_retry is not None,
        "workspace_blocked": state.workspace_blocked,
        "save_state": state.save_state,
        "workspace_status": dict(state.workspace_status),
        "phase": state.phase,
    }
    kind, text = agent_status(snapshot, strings, settings.llm_configured())
    llm = settings.llm()
    save = snapshot["save_state"]
    snapshot["entries"] = group_entries(with_transient(entries, state.errors, state.confirmation))
    snapshot.update({
        "run_active": state.running,
        "activity": activity_view(state, strings),
        "status_kind": kind,
        "status_text": text,
        "save_text": strings["save_%s" % save] if save else "",
        "t": strings,
        "language": settings.language(),
        "theme": settings.theme(),
        "settings": {
            "llm_base_url": llm["base_url"],
            "llm_model": llm["model"],
            "llm_key_saved": bool(llm["api_key"]),
        },
        "servers": _servers(settings, state.servers),
        "settings_notice": notice,
        "mcp_port": mcp_port() if callable(mcp_port) else mcp_port,
    })
    return snapshot
