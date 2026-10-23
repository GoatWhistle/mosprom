from ..ui.strings import strings_for
from .entries_view import agent_status, group_entries, with_result


def snapshot_of(state):
    return {
        "conversations": list(state.conversations),
        "conversation_id": state.conversation_id,
        "mode": state.mode,
        "entries": [dict(item) for item in state.entries],
        "run_id": state.run_id,
        "run_state": state.run_state,
        "run_active": state.run_active(),
        "progress": state.progress,
        "pending": state.pending,
        "result": state.result,
        "connection": state.connection,
        "notice": state.notice,
        "attachments": list(state.attachments),
        "busy": state.busy,
        "draft": state.draft,
        "draft_rev": state.draft_rev,
        "switching": state.switching,
        "switch_prompt": state.switch_prompt is not None,
        "can_retry_switch": state.switch_retry is not None,
        "workspace_blocked": state.workspace_blocked,
        "save_state": state.save_state,
        "project_version": state.project_version,
        "workspace_status": dict(state.workspace_status),
    }


def chat_view(state, settings, mcp_port, notice):
    snapshot = snapshot_of(state)
    strings = strings_for(settings.language())
    llm = settings.llm()
    kind, text = agent_status(snapshot, strings, settings.llm_configured())
    save = snapshot["save_state"]
    snapshot["entries"] = group_entries(with_result(snapshot["entries"], snapshot["result"]))
    result = snapshot["result"]
    stale = bool(result) and result.get("project_version") is not None \
        and snapshot["project_version"] > result["project_version"]
    snapshot.update({
        "result_stale": stale,
        "status_kind": kind,
        "status_text": text,
        "save_text": strings["save_%s" % save] if save else "",
        "t": strings,
        "language": settings.language(),
        "theme": settings.theme(),
        "settings": {
            "backend_url": settings.backend_url(),
            "llm_base_url": llm["base_url"],
            "llm_model": llm["model"],
            "llm_key_saved": bool(llm["api_key"]),
        },
        "settings_notice": notice,
        "mcp_port": mcp_port() if callable(mcp_port) else mcp_port,
    })
    return snapshot
