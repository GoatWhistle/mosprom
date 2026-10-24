import { action } from "./api.js";
import { h } from "./dom.js";

function field(label, input) {
  return h("label", { class: "field" }, h("span", { class: "field-label", text: label }), input);
}

function serverState(server, t) {
  let text = t["server_state_" + server.state] || server.state;
  if (server.state === "ok") text += " · " + server.tools + " " + t.tools_count;
  if (server.state === "error" && server.error) text += ": " + server.error;
  return text;
}

function choice(label, options, current, onPick) {
  return h("div", { class: "row" }, h("span", { class: "muted", text: label }),
    options.map(([value, title]) => h("button", { class: "btn" + (current === value ? " primary" : ""), type: "button",
      "aria-pressed": String(current === value), text: title, onclick: () => onPick(value) })));
}

export function settingsDraft(view) {
  const llm = view.settings || {};
  return { language: view.language, theme: view.theme, url: llm.llm_base_url || "", model: llm.llm_model || "", key: "",
    serverName: "", serverUrl: "", serverHeader: "" };
}

function bound(local, name, props) {
  return h("input", Object.assign({ value: local[name], autocomplete: "off", "data-field": name,
    oninput: (event) => { local[name] = event.target.value; } }, props));
}

export function renderSettings(host, view, local, close, report) {
  const t = view.t;
  const llm = view.settings || {};
  const focused = document.activeElement && host.contains(document.activeElement)
    ? { name: document.activeElement.getAttribute("data-field"), start: document.activeElement.selectionStart,
      end: document.activeElement.selectionEnd } : null;
  const url = bound(local, "url", { type: "url", placeholder: "https://" });
  const model = bound(local, "model", { type: "text" });
  const key = bound(local, "key", { type: "password", autocomplete: "new-password",
    placeholder: llm.llm_key_saved ? t.llm_key_saved : "" });
  const serverName = bound(local, "serverName", { type: "text" });
  const serverUrl = bound(local, "serverUrl", { type: "url", placeholder: "http://127.0.0.1:3001/mcp" });
  const serverHeader = bound(local, "serverHeader", { type: "text" });
  const rerender = () => renderSettings(host, view, local, close, report);
  const run = (promise) => promise.catch(report);

  host.replaceChildren(h("div", { class: "settings-panel", role: "dialog", "aria-modal": "true", "aria-label": t.settings },
    h("div", { class: "settings-head" }, h("h2", { text: t.settings }),
      h("button", { class: "icon-btn", type: "button", "aria-label": t.close, onclick: close, text: "×" })),
    h("h3", { text: t.llm_section }),
    field(t.llm_url, url), field(t.llm_model, model), field(t.llm_key, key),
    h("h3", { text: t.interface_section }),
    choice(t.language, [["ru", "RU"], ["en", "EN"]], local.language, (value) => { local.language = value; rerender(); }),
    choice(t.theme, [["dark", t.theme_dark], ["light", t.theme_light]], local.theme, (value) => { local.theme = value; rerender(); }),
    view.settings_notice ? h("div", { class: "notice", role: "status", text: view.settings_notice }) : null,
    h("div", { class: "row wrap" },
      h("button", { class: "btn primary", type: "button", text: t.save, onclick: () => run(
        action("applySettings", local.url, local.model, local.key, local.language, local.theme)
          .then((ok) => { if (ok) close(); })) }),
      h("button", { class: "btn", type: "button", text: t.check, onclick: () => run(action("checkConnection")) }),
      h("button", { class: "btn", type: "button", text: t.close, onclick: close })),
    h("hr"),
    h("h3", { text: t.servers }),
    h("p", { class: "muted", text: t.servers_hint }),
    (view.servers || []).map((server) => h("div", { class: "server" },
      h("div", { class: "server-name", text: server.name + (server.pinned ? " · " + t.server_builtin : "") }),
      server.url ? h("div", { class: "mono muted", text: server.url }) : null,
      h("div", { class: "server-state state-" + server.state, text: serverState(server, t) }),
      server.pinned ? null : h("div", { class: "row wrap" },
        h("button", { class: "btn", type: "button", text: server.enabled ? t.server_disable : t.server_enable,
          onclick: () => run(action("toggleServer", server.name, !server.enabled)) }),
        h("button", { class: "btn danger", type: "button", text: t.remove_server,
          onclick: () => run(action("removeServer", server.name)) })))),
    field(t.server_name, serverName), field(t.server_url, serverUrl), field(t.server_header, serverHeader),
    h("button", { class: "btn", type: "button", text: t.add_server, onclick: () => run(
      action("addServer", local.serverName, local.serverUrl, local.serverHeader).then((ok) => {
        if (ok) { local.serverName = ""; local.serverUrl = ""; local.serverHeader = ""; rerender(); }
      })) }),
    view.mcp_port !== null && view.mcp_port !== undefined ? h("p", { class: "muted", text: t.port_note + " " + view.mcp_port }) : null));
  if (focused && focused.name) {
    const input = host.querySelector('[data-field="' + focused.name + '"]');
    if (input) {
      input.focus();
      try { input.setSelectionRange(focused.start, focused.end); } catch (error) { }
    }
  }
}
