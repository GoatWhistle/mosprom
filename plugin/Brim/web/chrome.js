import { h } from "./dom.js";

const $ = (id) => document.getElementById(id);

export function renderSidebar(view, list, handlers) {
  const t = view.t;
  $("new-chat").textContent = "+  " + t.new_chat;
  $("new-from-scene").textContent = t.new_from_scene;
  $("new-from-scene").disabled = !!view.busy || !!view.switching;
  $("chats-title").textContent = t.chats;
  const rows = view.conversations || [];
  list.replaceChildren(...(rows.length ? rows.map((row) => {
    const current = row.id === view.conversation_id;
    const stamp = (row.updated_at || "").slice(0, 16).replace("T", " ");
    const sub = current ? (view.run_active ? view.status_text : view.save_text) || stamp : stamp;
    return h("button", { class: "chat-row" + (current ? " current" : ""), type: "button", "aria-current": current ? "true" : null,
      onclick: () => handlers.open(row.id) },
      h("span", { class: "chat-title", text: row.title || stamp }),
      h("span", { class: "chat-sub" + (current && view.status_kind === "busy" ? " accent" : ""), text: sub }));
  }) : [h("div", { class: "muted small", text: t.no_chats })]));
}

export function renderHeader(view, modeHost, setMode) {
  const t = view.t;
  const current = (view.conversations || []).find((row) => row.id === view.conversation_id);
  $("title").textContent = current && current.title ? current.title : t.new_chat;
  $("status").textContent = view.status_text + (view.save_text ? "  ·  " + view.save_text : "");
  $("status").className = "status" + (view.status_kind === "error" ? " danger" : "");
  $("status-dot").className = "status-dot " + view.status_kind;
  modeHost.replaceChildren(...["auto", "ask"].map((mode) => h("button", { type: "button", role: "radio",
    class: view.mode === mode ? "on" : "", "aria-checked": String(view.mode === mode), title: t["mode_" + mode + "_hint"],
    text: t["mode_" + mode], onclick: () => setMode(mode) })));
  for (const [id, label] of [["menu", t.menu], ["settings", t.settings], ["open-folder", t.open_folder]]) {
    $(id).setAttribute("aria-label", label);
    $(id).title = label;
  }
}
