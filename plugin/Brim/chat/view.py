from ..ui.strings import strings_for


def chat_view(state, settings, mcp_port, notice):
    snapshot = state.snapshot()
    strings = strings_for(settings.language())
    llm = settings.llm()
    snapshot.update({
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

