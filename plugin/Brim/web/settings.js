import { action } from "./api.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";
import { readMs } from "./motion.js";
import { renderSegmented } from "./segmented.js";
import { buildServers, field, input, renderServers } from "./servers.js";

export function settingsDraft(view) {
  const llm = view.settings || {};
  return { language: view.language, theme: view.theme, url: llm.llm_base_url || "", model: llm.llm_model || "", key: "",
    serverName: "", serverUrl: "", serverHeader: "", adding: false, noticeOwner: null, saved: false };
}

function dirty(local, view) {
  const llm = view.settings || {};
  return local.url !== (llm.llm_base_url || "") || local.model !== (llm.llm_model || "") || local.key !== "";
}

function build(host, local, handlers) {
  const run = (promise) => promise.catch(handlers.report);
  const refresh = () => { if (host.view) renderSettings(host, host.view, local, handlers); };
  const refs = {
    title: h("h2", { class: "drawer-title" }),
    close: h("button", { class: "icon-button", type: "button", onclick: handlers.close }, icon("close")),
    llmTitle: h("h3", { class: "settings-heading" }),
    status: h("div", { class: "settings-status" }),
    fields: {
      url: field("llm_address", input(local, "url", { type: "url", placeholder: "https://host/v1" }, refresh), true),
      model: field("llm_model", input(local, "model", { type: "text" }, refresh), true),
      key: field("llm_key_short", input(local, "key", { type: "password", autocomplete: "new-password" }, refresh)),
    },
    save: h("button", { class: "button button-compact", type: "button" }),
    check: h("button", { class: "button button-secondary button-compact", type: "button" }),
    saved: h("span", { class: "settings-saved", role: "status" }),
    notice: h("div", { role: "status" }),
    interfaceTitle: h("h3", { class: "settings-heading" }),
    languageLabel: h("span"),
    language: h("div", { class: "segmented" }),
    themeLabel: h("span"),
    theme: h("div", { class: "segmented" }),
  };
  refs.servers = buildServers(local, run);
  refs.servers.render = refresh;
  refs.save.onclick = () => {
    local.noticeOwner = "llm";
    run(action("applySettings", local.url, local.model, local.key, local.language, local.theme).then((ok) => {
      if (!ok) return;
      local.key = "";
      refs.fields.key.node.querySelector("input").value = "";
      local.saved = true;
      clearTimeout(refs.savedTimer);
      refs.savedTimer = setTimeout(() => { local.saved = false; refresh(); }, readMs("--dur-banner"));
      refresh();
    }));
  };
  refs.check.onclick = () => { local.noticeOwner = "llm"; run(action("checkConnection")); };
  const drawer = h("aside", { class: "drawer", role: "dialog", "aria-modal": "true" },
    h("div", { class: "drawer-head" }, refs.title, refs.close),
    h("div", { class: "drawer-body" },
      h("section", { class: "settings-section" },
        refs.llmTitle,
        h("div", { class: "settings-panel" }, refs.status, Object.values(refs.fields).map((item) => item.node),
          h("div", { class: "settings-actions" }, refs.save, refs.check, refs.saved), refs.notice)),
      h("section", { class: "settings-section" },
        refs.interfaceTitle,
        h("div", { class: "settings-panel" },
          h("div", { class: "settings-row" }, refs.languageLabel, refs.language),
          h("div", { class: "settings-row" }, refs.themeLabel, refs.theme))),
      refs.servers.node));
  host.replaceChildren(h("div", { class: "scrim", onclick: handlers.close }), drawer);
  host.refs = refs;
  return refs;
}

function renderStatus(refs, view, local) {
  const t = view.t;
  const llm = view.settings || {};
  const notice = local.noticeOwner === "llm" ? view.settings_notice || "" : "";
  const failed = notice.indexOf(t.check_failed) === 0;
  const passed = notice.indexOf(t.check_ok) === 0;
  const configured = !!(llm.llm_base_url && llm.llm_model);
  const kind = !configured ? "warning" : failed ? "error" : passed ? "ok" : "idle";
  const text = !configured ? t.llm_not_set : failed || passed ? notice : t.llm_unchecked;
  refs.status.replaceChildren(h("span", { class: "status-dot status-dot-" + kind }),
    h("span", { class: "settings-status-text settings-status-" + kind, text }));
  const other = notice && !failed && !passed ? notice : "";
  refs.notice.className = other ? "banner banner-danger" : "";
  refs.notice.textContent = other;
}

export function renderSettings(host, view, local, handlers) {
  const t = view.t;
  const llm = view.settings || {};
  host.view = view;
  const refs = host.refs || build(host, local, handlers);
  host.querySelector(".drawer").setAttribute("aria-label", t.settings);
  refs.title.textContent = t.settings;
  refs.close.setAttribute("aria-label", t.close);
  refs.llmTitle.textContent = t.llm_section;
  for (const item of Object.values(refs.fields)) item.label.textContent = t[item.name];
  refs.fields.key.hint.textContent = llm.llm_key_saved ? t.llm_key_saved : "";
  refs.fields.key.hint.hidden = !llm.llm_key_saved;
  renderStatus(refs, view, local);
  refs.save.textContent = t.save;
  refs.save.disabled = !dirty(local, view);
  refs.check.textContent = t.check;
  refs.saved.replaceChildren(icon("check", "sm"), t.saved);
  refs.saved.hidden = !local.saved;
  refs.interfaceTitle.textContent = t.interface_section;
  refs.languageLabel.textContent = t.language;
  refs.themeLabel.textContent = t.theme;
  const themes = [{ value: "dark", text: t.theme_dark, icon: "moon" }, { value: "light", text: t.theme_light, icon: "sun" }];
  const pick = (name) => (value) => {
    local[name] = value;
    if (name === "theme") {
      renderSegmented(refs.theme, themes, value, pick("theme"));
      requestAnimationFrame(() => handlers.previewTheme(value));
    } else renderSettings(host, view, local, handlers);
    setTimeout(() => action("setInterface", local.language, local.theme).catch(handlers.report));
  };
  renderSegmented(refs.language, [{ value: "ru", text: "Русский" }, { value: "en", text: "English" }], local.language, pick("language"));
  renderSegmented(refs.theme, themes, local.theme, pick("theme"));
  renderServers(refs.servers, view, local, (promise) => promise.catch(handlers.report));
}

export function resetSettings(host) {
  if (host.refs) clearTimeout(host.refs.savedTimer);
  host.refs = null;
  host.view = null;
  host.replaceChildren();
}
