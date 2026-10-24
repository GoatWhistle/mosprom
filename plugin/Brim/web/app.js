import { action, openPath, poll, token, upload } from "./api.js";
import { brandLockup, brandMark } from "./brand.js";
import { h } from "./dom.js";
import { renderComposer, syncSend } from "./composer.js";
import { bindDrop } from "./drop.js";
import { renderEmpty } from "./empty.js";
import { renderHeader, renderSidebar } from "./chrome.js";
import { hydrateIcons, icon } from "./icons.js";
import { renderSettings, resetSettings, settingsDraft } from "./settings.js";
import { renderStatus, tickClocks } from "./status.js";
import { leave, readMs, scrambleText, switchTheme, warmMotion } from "./motion.js";
import { offline, setBanner } from "./banner.js";
import { createTimeline } from "./timeline.js";
import { createPanels } from "./panels.js";

const DRAFT_DELAY_MS = 300;

const $ = (id) => document.getElementById(id);
const ui = {
  app: $("app"), sidebar: $("sidebar"), scrim: $("scrim"), chatList: $("chat-list"), timeline: $("timeline"),
  entries: $("entries"), empty: $("empty"), input: $("input"), attachments: $("attachments"), status: $("status-area"),
  banner: $("banner"), bannerSlot: $("banner-slot"), file: $("file"), drop: $("drop"), settingsHost: $("settings-host"),
  skill: $("skill"), jump: $("jump"), splash: $("splash"), suggestions: $("suggestions"),
};
const state = { view: null, expanded: {}, rendered: [], conversation: "\u0000", draftRev: -1, draftTimer: null,
  followEnd: true, settings: null, pendingTheme: null, switching: false, queued: null, uploading: [], theme: null, language: null };

const showBanner = (text, kind) => setBanner(ui.bannerSlot, ui.banner, text, kind);

function showError(error) {
  showBanner(state.view ? (state.view.t.error || "") + ": " + error.message : error.message, "danger");
  clearTimeout(showError.timer);
  showError.timer = setTimeout(() => { showError.timer = null; showBanner(""); }, readMs("--dur-banner"));
}

function fillInput(text) {
  ui.input.value = text;
  ui.input.focus();
  ui.input.setSelectionRange(text.length, text.length);
  scheduleDraft();
}

const ctx = {
  get view() { return state.view; },
  get t() { return state.view.t; },
  isExpanded: (key) => !!state.expanded[key],
  setExpanded: (key, value) => { state.expanded[key] = value; },
  pickOption: (line, single) => {
    if (single && !ui.input.value.trim()) {
      ui.input.value = line;
      send();
      return;
    }
    fillInput(ui.input.value.trim() === "" ? line : ui.input.value + "\n" + line);
  },
  confirm: (decision) => action("confirm", decision, ui.input.value).catch(showError),
  openFolder: (path) => openPath(path).catch(showError),
};

const timeline = createTimeline(ui, state, ctx);
const panels = createPanels(ui, state);
const closeDrawer = panels.closeDrawer;

function applyTheme(theme, after) {
  const set = () => {
    document.documentElement.dataset.theme = theme;
    if (after) after();
  };
  if (state.theme === null) set();
  else if (state.theme !== theme) {
    state.switching = true;
    switchTheme(theme, set).finally(() => {
      state.switching = false;
      const queued = state.queued;
      state.queued = null;
      if (queued) render(queued);
    });
  } else if (after) after();
  state.theme = theme;
}

function previewTheme(theme, after) {
  state.pendingTheme = theme;
  applyTheme(theme, after);
}

const settingsHandlers = { close: () => closeSettings(), report: (error) => { state.pendingTheme = null; showError(error); },
  previewTheme };

function receive(view) {
  if (state.switching) state.queued = view;
  else render(view);
}

function hideSplash() {
  if (!ui.splash) return;
  const splash = ui.splash;
  ui.splash = null;
  leave(splash, () => splash.remove());
}

function render(view) {
  state.view = view;
  const language = view.language === "en" ? "en" : "ru";
  const served = view.theme === "light" ? "light" : "dark";
  if (state.pendingTheme === served) state.pendingTheme = null;
  const theme = state.pendingTheme || served;
  const relabel = state.language !== null && state.language !== language;
  state.language = language;
  document.documentElement.lang = language;
  applyTheme(theme);
  $("empty-title").textContent = view.t.empty_title;
  renderEmpty(ui.suggestions, view, fillInput);
  ui.jump.replaceChildren(icon("down", "sm"), h("span", { text: view.t.new_messages }));
  renderSidebar(view, ui.chatList, { open: (id) => { closeDrawer(); action("openChat", id).catch(showError); } });
  renderHeader(view, (mode) => action("setMode", mode).catch(showError));
  timeline.render();
  renderStatus(ui.status, view, showError);
  renderComposer(ui, view, state, showError);
  if (state.settings) renderSettings(ui.settingsHost, view, state.settings, settingsHandlers);
  panels.label();
  if (relabel) scrambleText();
  hideSplash();
}

function scheduleDraft() {
  clearTimeout(state.draftTimer);
  state.draftTimer = setTimeout(() => action("setDraft", ui.input.value).catch(() => {}), DRAFT_DELAY_MS);
  if (state.view) syncSend(ui, state.view, state);
}

function send() {
  if (!state.view || state.view.busy || state.view.run_active) return;
  clearTimeout(state.draftTimer);
  action("send", ui.input.value).catch(showError);
  timeline.scrollToEnd();
}

async function attachFiles(files) {
  for (const file of Array.from(files)) {
    state.uploading.push(file.name);
    if (state.view) renderComposer(ui, state.view, state, showError);
    try {
      await upload(file);
    } catch (error) {
      showError(new Error((state.view ? state.view.t.upload_failed : "Upload failed") + " — " + file.name + ": " + error.message));
    } finally {
      state.uploading.splice(state.uploading.indexOf(file.name), 1);
      if (state.view) renderComposer(ui, state.view, state, showError);
    }
  }
  ui.input.focus();
}

function openSettings() {
  if (!state.view || state.settings) return;
  state.settings = settingsDraft(state.view);
  ui.settingsHost.hidden = false;
  renderSettings(ui.settingsHost, state.view, state.settings, settingsHandlers);
  const first = ui.settingsHost.querySelector("input");
  if (first) first.focus();
}

function closeSettings() {
  if (!state.settings) return;
  state.settings = null;
  leave(ui.settingsHost, () => {
    if (state.settings) return;
    ui.settingsHost.hidden = true;
    resetSettings(ui.settingsHost);
  });
  $("settings").focus();
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
  $("menu").addEventListener("click", panels.openDrawer);
  $("sidebar-toggle").addEventListener("click", panels.toggle);
  ui.scrim.addEventListener("click", closeDrawer);
  ui.jump.addEventListener("click", timeline.scrollToEnd);
  ui.timeline.addEventListener("scroll", () => {
    state.followEnd = timeline.atEnd();
    if (state.followEnd) ui.jump.hidden = true;
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.settings) closeSettings();
    else if (event.key === "Escape") closeDrawer();
  });
  bindDrop(ui.drop, () => !!(state.view && state.view.busy), attachFiles);
  setInterval(() => tickClocks(ui.status), 250);
}

function boot() {
  hydrateIcons(document.body);
  requestAnimationFrame(warmMotion);
  $("brand").replaceChildren(brandLockup("intro"));
  $("empty-mark").replaceWith(brandMark("intro"));
  $("splash-mark").replaceWith(brandMark(token ? "loop" : null));
  panels.restore();
  bind();
  if (!token) {
    $("splash").dataset.kind = "error";
    $("splash-text").textContent = offline().no_token;
    return;
  }
  $("splash-text").textContent = offline().connecting;
  poll(receive, (error) => {
    if (!error) {
      if (!showError.timer) showBanner("");
      return;
    }
    const text = error.status === 401 ? offline().no_token : state.view ? state.view.t.connection_lost : offline().connecting;
    if (ui.splash) {
      ui.splash.dataset.kind = error.status === 401 ? "error" : "";
      $("splash-text").textContent = text;
    } else showBanner(text, error.status === 401 ? "danger" : "");
  });
}

boot();
