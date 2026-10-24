import { spinner } from "./brand.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";
import { renderSegmented } from "./segmented.js";

const $ = (id) => document.getElementById(id);
const DAY_MS = 86400000;
const SAVE_ICONS = { saved: "check", failed: "alert" };

function labelled(id, name, text) {
  $(id).replaceChildren(icon(name, "sm"), h("span", { text }));
}

function parse(value) {
  const date = new Date(value || "");
  return isNaN(date.getTime()) ? null : date;
}

function dayLabel(date, locale) {
  const start = (value) => new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime();
  const days = Math.round((start(date) - start(new Date())) / DAY_MS);
  if (days === 0 || days === -1) {
    const text = new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(days, "day");
    return text.charAt(0).toUpperCase() + text.slice(1);
  }
  return date.toLocaleDateString(locale, { day: "numeric", month: "long" });
}

function placeIndicator(list) {
  const indicator = list.querySelector(".chat-indicator");
  const row = list.querySelector('.chat-row[aria-current="true"]');
  if (!indicator) return;
  if (!row) {
    indicator.hidden = true;
    return;
  }
  indicator.hidden = false;
  indicator.style.blockSize = row.offsetHeight + "px";
  indicator.style.translate = "0 " + row.offsetTop + "px";
  if (!indicator.dataset.ready) requestAnimationFrame(() => { indicator.dataset.ready = "true"; });
}

function select(list, id) {
  list.pending = id;
  for (const row of list.querySelectorAll(".chat-row")) row.setAttribute("aria-current", String(row.dataset.id === id));
  placeIndicator(list);
}

export function renderSidebar(view, list, handlers) {
  const t = view.t;
  const locale = view.language === "en" ? "en" : "ru";
  labelled("new-chat", "plus", t.new_chat);
  labelled("new-from-scene", "scene", t.new_from_scene);
  $("new-from-scene").disabled = !!view.busy || !!view.switching;
  list.setAttribute("aria-label", t.chats);
  const known = list.known || null;
  list.known = new Set();
  if (list.pending === view.conversation_id || view.switch_prompt) list.pending = null;
  const selected = list.pending || view.conversation_id;
  let indicator = list.querySelector(".chat-indicator");
  if (!indicator) {
    indicator = h("span", { class: "chat-indicator", "aria-hidden": "true" });
    list.prepend(indicator);
  }
  const nodes = [];
  let group = null;
  for (const row of view.conversations || []) {
    const date = parse(row.updated_at);
    const label = date ? dayLabel(date, locale) : "";
    if (label !== group) {
      group = label;
      nodes.push(h("div", { class: "chat-group", text: label }));
    }
    const current = row.id === selected;
    const busy = row.id === view.conversation_id && view.run_active;
    list.known.add(row.id);
    nodes.push(h("button", { class: "chat-row" + (known && !known.has(row.id) ? " chat-row-new" : ""), type: "button",
      "data-id": row.id, "aria-current": String(current),
      onclick: () => { select(list, row.id); handlers.open(row.id); } },
      h("span", { class: "chat-row-title", text: row.title || t.new_chat }),
      h("span", { class: "chat-row-time", text: date ? date.toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" }) : "" }),
      busy ? h("span", { class: "chat-row-status" }, spinner(), h("span", { text: view.status_text })) : null));
  }
  if (!nodes.length) nodes.push(h("div", { class: "chat-list-empty", text: t.no_chats }));
  while (list.lastChild && list.lastChild !== indicator) list.lastChild.remove();
  list.append(...nodes);
  placeIndicator(list);
}

function metaItem(className, lead, text) {
  return h("span", { class: "header-meta-item " + className }, lead, h("span", { text }));
}

function renderMeta(view) {
  const host = $("status");
  const kind = view.status_kind;
  let state = host.querySelector(".header-state");
  if (!state || state.dataset.kind !== kind) {
    state = metaItem("header-state header-state-" + kind,
      kind === "busy" ? spinner() : h("span", { class: "status-dot status-dot-" + kind }), "");
    state.dataset.kind = kind;
  }
  state.lastChild.textContent = view.status_text;
  const save = view.save_state ? metaItem("header-save header-save-" + view.save_state,
    SAVE_ICONS[view.save_state] ? icon(SAVE_ICONS[view.save_state], "sm") : null, view.save_text) : null;
  if (host.firstChild !== state) host.replaceChildren(state);
  while (host.childNodes.length > 1) host.lastChild.remove();
  if (save) host.append(save);
}

export function renderHeader(view, setMode) {
  const t = view.t;
  const current = (view.conversations || []).find((row) => row.id === view.conversation_id);
  $("title").textContent = current && current.title ? current.title : t.new_chat;
  renderMeta(view);
  renderSegmented($("mode"), ["auto", "ask"].map((mode) => ({ value: mode, text: t["mode_" + mode], title: t["mode_" + mode + "_hint"] })),
    view.mode, setMode);
  for (const [id, label] of [["menu", t.menu], ["settings", t.settings], ["open-folder", t.open_folder]]) {
    $(id).setAttribute("aria-label", label);
    $(id).title = label;
  }
}
