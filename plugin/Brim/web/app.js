import { action, openPath, poll, token, upload } from "./api.js";
import { chip, h } from "./dom.js";
import { bindDrop } from "./drop.js";
import { buildEntry } from "./entries.js";
import { renderHeader, renderSidebar } from "./chrome.js";
import { renderSettings, settingsDraft } from "./settings.js";
import { renderStatus, tickClocks } from "./status.js";

const OFFLINE = {
  ru: { connecting: "Подключаюсь к слайсеру…", no_token: "Откройте чат из меню слайсера: Brim → Открыть в браузере" },
  en: { connecting: "Connecting to the slicer…", no_token: "Open the chat from the slicer menu: Brim → Open in browser" },
};
const DRAFT_DELAY_MS = 300;

const $ = (id) => document.getElementById(id);
const ui = {
  app: $("app"), sidebar: $("sidebar"), scrim: $("scrim"), chatList: $("chat-list"), timeline: $("timeline"),
  entries: $("entries"), empty: $("empty"), input: $("input"), attachments: $("attachments"), status: $("status-area"),
  banner: $("banner"), file: $("file"), drop: $("drop"), settingsHost: $("settings-host"), skill: $("skill"),
  jump: $("jump"), mode: $("mode"),
};
const state = { view: null, expanded: {}, rendered: [], conversation: "\u0000", draftRev: -1, draftTimer: null,
  followEnd: true, settings: null, uploading: [] };

function offline() {
  return OFFLINE[navigator.language && navigator.language.startsWith("ru") ? "ru" : "en"];
}

function showError(error) {
  ui.banner.hidden = false;
  ui.banner.textContent = state.view ? (state.view.t.error || "") + ": " + error.message : error.message;
  clearTimeout(showError.timer);
  showError.timer = setTimeout(() => { showError.timer = null; ui.banner.hidden = true; }, 6000);
}

const ctx = {
  get view() { return state.view; },
  get t() { return state.view.t; },
  isExpanded: (key) => !!state.expanded[key],
  toggle: (key) => { state.expanded[key] = !state.expanded[key]; state.rendered = []; renderEntries(); },
  pickOption: (line) => {
    ui.input.value = ui.input.value === "" ? line : ui.input.value + "\n" + line;
    ui.input.focus();
    scheduleDraft();
  },
  confirm: (decision) => action("confirm", decision, ui.input.value).catch(showError),
  openFolder: (path) => openPath(path).catch(showError),
};

function atEnd() {
  const node = ui.timeline;
  return node.scrollHeight - node.scrollTop - node.clientHeight < 24;
}

function scrollToEnd() {
  ui.timeline.scrollTop = ui.timeline.scrollHeight;
  state.followEnd = true;
  ui.jump.hidden = true;
}

function renderEntries() {
  const entries = state.view.entries || [];
  const switched = state.view.conversation_id !== state.conversation;
  if (switched) {
    state.conversation = state.view.conversation_id;
    state.rendered = [];
    ui.entries.replaceChildren();
  }
  const follow = switched || state.followEnd;
  let keep = 0;
  while (keep < entries.length && keep < state.rendered.length && state.rendered[keep].key === entries[keep].key) keep++;
  const nodes = Array.from(ui.entries.children);
  for (let index = 0; index < keep; index++) {
    const payload = JSON.stringify(entries[index]);
    if (state.rendered[index].payload !== payload) {
      const node = buildEntry(entries[index], ctx);
      nodes[index].replaceWith(node);
      state.rendered[index] = { key: entries[index].key, payload };
    }
  }
  for (const node of nodes.slice(keep)) node.remove();
  state.rendered.length = keep;
  for (let index = keep; index < entries.length; index++) {
    const node = buildEntry(entries[index], ctx);
    if (!switched) node.classList.add("fresh");
    ui.entries.append(node);
    state.rendered.push({ key: entries[index].key, payload: JSON.stringify(entries[index]) });
  }
  ui.empty.hidden = entries.length > 0;
  if (follow) scrollToEnd();
  else if (entries.length > keep) ui.jump.hidden = false;
}

function renderComposer(view) {
  const t = view.t;
  if (view.draft_rev !== state.draftRev) {
    state.draftRev = view.draft_rev;
    if (document.activeElement !== ui.input || view.draft === "") ui.input.value = view.draft || "";
  }
  ui.input.placeholder = t.placeholder;
  ui.input.setAttribute("aria-label", t.placeholder);
  $("composer-hint").textContent = t.composer_hint;
  $("drop-text").textContent = t.drop_files;
  const attach = $("attach");
  attach.disabled = !!view.busy;
  attach.title = t.attach_hint;
  attach.setAttribute("aria-label", t.attach);
  $("send").hidden = !!view.run_active;
  $("send").disabled = !!view.busy;
  $("send").setAttribute("aria-label", t.send);
  $("stop").hidden = !view.run_active;
  $("stop").disabled = !!view.stopping;
  $("stop").setAttribute("aria-label", t.stop);
  const chips = (view.attachments || []).map((item, index) => chip(item.name,
    () => action("removeAttachment", index).catch(showError), t.remove));
  ui.attachments.replaceChildren(...chips, ...state.uploading.map((name) => {
    const node = chip(name);
    node.classList.add("uploading");
    return node;
  }));
  const options = view.skill_options || [];
  ui.skill.hidden = options.length === 0;
  ui.skill.title = t.skill_hint;
  ui.skill.setAttribute("aria-label", t.skill_hint);
  ui.skill.replaceChildren(...options.map((item) => h("option", { value: item.name, text: item.title })));
  ui.skill.value = view.skill || "";
}

function render(view) {
  state.view = view;
  document.documentElement.lang = view.language === "en" ? "en" : "ru";
  document.documentElement.dataset.theme = view.theme === "light" ? "light" : "dark";
  $("empty-title").textContent = view.t.empty_title;
  $("empty-body").textContent = view.t.empty_body;
  $("jump").textContent = "↓  " + view.t.new_messages;
  renderSidebar(view, ui.chatList, { open: (id) => { closeDrawer(); action("openChat", id).catch(showError); } });
  renderHeader(view, ui.mode, (mode) => action("setMode", mode).catch(showError));
  renderEntries();
  renderStatus(ui.status, view, showError);
  renderComposer(view);
  if (state.settings) renderSettings(ui.settingsHost, view, state.settings, closeSettings, showError);
}

function scheduleDraft() {
  clearTimeout(state.draftTimer);
  state.draftTimer = setTimeout(() => action("setDraft", ui.input.value).catch(() => {}), DRAFT_DELAY_MS);
}

function send() {
  if (!state.view || state.view.busy || state.view.run_active) return;
  clearTimeout(state.draftTimer);
  action("send", ui.input.value).catch(showError);
  scrollToEnd();
}

async function attachFiles(files) {
  for (const file of Array.from(files)) {
    state.uploading.push(file.name);
    if (state.view) renderComposer(state.view);
    try {
      await upload(file);
    } catch (error) {
      showError(new Error((state.view ? state.view.t.upload_failed : "Upload failed") + " — " + file.name + ": " + error.message));
    } finally {
      state.uploading.splice(state.uploading.indexOf(file.name), 1);
      if (state.view) renderComposer(state.view);
    }
  }
  ui.input.focus();
}

function openSettings() {
  if (!state.view) return;
  state.settings = settingsDraft(state.view);
  ui.settingsHost.hidden = false;
  renderSettings(ui.settingsHost, state.view, state.settings, closeSettings, showError);
  const first = ui.settingsHost.querySelector("input");
  if (first) first.focus();
}

function closeSettings() {
  state.settings = null;
  ui.settingsHost.hidden = true;
  ui.settingsHost.replaceChildren();
}

function closeDrawer() {
  ui.app.classList.remove("drawer-open");
  ui.scrim.hidden = true;
}

function bind() {
  $("composer").addEventListener("submit", (event) => { event.preventDefault(); send(); });
  ui.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(); }
  });
  ui.input.addEventListener("input", scheduleDraft);
  $("attach").addEventListener("click", () => ui.file.click());
  ui.file.addEventListener("change", () => { attachFiles(ui.file.files); ui.file.value = ""; });
  $("stop").addEventListener("click", () => action("stop").catch(showError));
  ui.skill.addEventListener("change", () => action("setSkill", ui.skill.value).catch(showError));
  $("new-chat").addEventListener("click", () => { closeDrawer(); action("newChat").catch(showError); });
  $("new-from-scene").addEventListener("click", () => { closeDrawer(); action("newChatFromScene").catch(showError); });
  $("settings").addEventListener("click", openSettings);
  $("open-folder").addEventListener("click", () => action("openFolder").catch(showError));
  $("menu").addEventListener("click", () => { ui.app.classList.add("drawer-open"); ui.scrim.hidden = false; });
  ui.scrim.addEventListener("click", closeDrawer);
  ui.jump.addEventListener("click", scrollToEnd);
  ui.timeline.addEventListener("scroll", () => {
    state.followEnd = atEnd();
    if (state.followEnd) ui.jump.hidden = true;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.settings) closeSettings();
    else if (event.key === "Escape") closeDrawer();
  });
  bindDrop(ui.drop, () => !!(state.view && state.view.busy), attachFiles);
  setInterval(() => tickClocks(ui.status), 250);
}

bind();
if (!token) {
  ui.banner.hidden = false;
  ui.banner.textContent = offline().no_token;
} else {
  ui.banner.hidden = false;
  ui.banner.textContent = offline().connecting;
  poll(render, (error) => {
    if (!error) {
      if (!showError.timer) ui.banner.hidden = true;
      return;
    }
    ui.banner.hidden = false;
    ui.banner.textContent = error.status === 401 ? offline().no_token
      : state.view ? state.view.t.connection_lost : offline().connecting;
  });
}
