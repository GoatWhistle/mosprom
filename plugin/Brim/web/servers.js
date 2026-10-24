import { action } from "./api.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";

const DOT = { ok: "ok", error: "error", off: "idle", unknown: "idle" };

export function field(name, input, required) {
  const label = h("span");
  const mark = required ? h("span", { class: "field-required", "aria-hidden": "true", text: "*" }) : null;
  const hint = h("span", { class: "field-hint", hidden: true });
  if (required) input.required = true;
  return { name, node: h("label", { class: "field" }, h("span", { class: "field-label" }, label, mark), input, hint), label, hint };
}

export function input(local, name, props, changed) {
  return h("input", Object.assign({ class: "field-input", value: local[name], autocomplete: "off", spellcheck: "false",
    oninput: (event) => { local[name] = event.target.value; if (changed) changed(); } }, props));
}

function serverMeta(server, t) {
  if (server.state === "error") return (t.server_state_error || "") + (server.error ? ": " + server.error : "");
  return t["server_state_" + server.state] || server.state;
}

export function buildServers(local, run) {
  const refs = {};
  const clear = () => {
    for (const name of ["serverName", "serverUrl", "serverHeader"]) { local[name] = ""; refs.fields[name].node.querySelector("input").value = ""; }
  };
  refs.title = h("h3", { class: "settings-heading" });
  refs.list = h("div", { class: "server-list" });
  refs.fields = {
    serverName: field("server_name_short", input(local, "serverName", { type: "text", placeholder: "docs" }), true),
    serverUrl: field("server_url", input(local, "serverUrl", { type: "url", placeholder: "http://127.0.0.1:3001/mcp" }), true),
    serverHeader: field("server_header_short", input(local, "serverHeader", { type: "text", placeholder: "Authorization: Bearer …" })),
  };
  refs.add = h("button", { class: "button button-compact", type: "button" });
  refs.cancel = h("button", { class: "button button-ghost button-compact", type: "button" });
  refs.notice = h("div", { role: "status" });
  refs.form = h("div", { class: "settings-panel server-form" },
    Object.values(refs.fields).map((item) => item.node), refs.notice, h("div", { class: "settings-actions" }, refs.add, refs.cancel));
  refs.open = h("button", { class: "button button-secondary button-compact", type: "button" });
  refs.port = h("p", { class: "mono settings-port" });
  refs.add.onclick = () => {
    local.noticeOwner = "servers";
    run(action("addServer", local.serverName, local.serverUrl, local.serverHeader).then((ok) => {
      if (!ok) return;
      clear();
      local.adding = false;
      refs.render();
    }));
  };
  refs.cancel.onclick = () => { clear(); local.adding = false; refs.render(); };
  refs.open.onclick = () => {
    local.adding = true;
    refs.render();
    refs.fields.serverName.node.querySelector("input").focus();
  };
  refs.node = h("section", { class: "settings-section" },
    refs.title, refs.list, refs.form, refs.open, refs.port);
  return refs;
}

function serverRow(server, t, run, local) {
  const toggle = () => { local.noticeOwner = "servers"; run(action("toggleServer", server.name, !server.enabled)); };
  const remove = () => { local.noticeOwner = "servers"; run(action("removeServer", server.name)); };
  return h("div", { class: "server" },
    h("span", { class: "status-dot status-dot-" + (DOT[server.state] || "idle") }),
    h("div", { class: "server-text" },
      h("div", { class: "server-name" }, server.name, server.pinned ? h("span", { class: "server-badge", text: t.server_builtin }) : null),
      h("div", { class: "server-meta" + (server.state === "error" ? " server-meta-error" : "") },
        h("span", { text: serverMeta(server, t) }),
        server.state === "ok" ? h("span", { class: "tag", text: server.tools + " " + t.tools_count }) : null),
      server.url ? h("div", { class: "mono server-meta", text: server.url }) : null),
    server.pinned ? null : h("div", { class: "server-controls" },
      h("button", { class: "switch", type: "button", role: "switch", "aria-checked": String(!!server.enabled),
        "aria-label": (server.enabled ? t.server_disable : t.server_enable) + " " + server.name, onclick: toggle }),
      h("button", { class: "icon-button", type: "button", "aria-label": t.remove_server + " " + server.name,
        title: t.remove_server, onclick: remove }, icon("trash", "sm"))));
}

export function renderServers(refs, view, local, run) {
  const t = view.t;
  refs.title.textContent = t.servers;
  refs.list.replaceChildren(...(view.servers || []).map((server) => serverRow(server, t, run, local)));
  for (const item of Object.values(refs.fields)) item.label.textContent = t[item.name];
  refs.add.textContent = t.add_server;
  refs.cancel.textContent = t.cancel;
  refs.open.replaceChildren(icon("plus", "sm"), h("span", { text: t.add_server }));
  refs.form.hidden = !local.adding;
  refs.open.hidden = !!local.adding;
  const notice = local.noticeOwner === "servers" ? view.settings_notice : "";
  refs.notice.className = notice ? "banner banner-danger" : "";
  refs.notice.textContent = notice || "";
  refs.port.textContent = view.mcp_port !== null && view.mcp_port !== undefined ? t.port_note + " " + view.mcp_port : "";
  refs.port.hidden = !refs.port.textContent;
}
