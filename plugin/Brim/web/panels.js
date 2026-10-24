import { leave } from "./motion.js";

const STORAGE_KEY = "brim-sidebar";
const $ = (id) => document.getElementById(id);

export function createPanels(ui, state) {
  function collapsed() {
    return ui.app.dataset.sidebar === "collapsed";
  }

  function label() {
    const toggle = $("sidebar-toggle");
    toggle.setAttribute("aria-expanded", String(!collapsed()));
    if (!state.view) return;
    const t = state.view.t;
    toggle.setAttribute("aria-label", collapsed() ? t.sidebar_expand : t.sidebar_collapse);
    toggle.title = toggle.getAttribute("aria-label");
    $("new-chat").title = t.new_chat;
    $("new-from-scene").title = t.new_from_scene;
  }

  function setCollapsed(value) {
    ui.app.dataset.sidebar = value ? "collapsed" : "open";
    ui.chatList.inert = value;
    try { localStorage.setItem(STORAGE_KEY, value ? "collapsed" : "open"); } catch (error) { }
    label();
  }

  function restore() {
    let value = false;
    try { value = localStorage.getItem(STORAGE_KEY) === "collapsed"; } catch (error) { }
    setCollapsed(value);
    requestAnimationFrame(() => requestAnimationFrame(() => { ui.app.dataset.ready = "true"; }));
  }

  function openDrawer() {
    ui.app.dataset.drawer = "open";
    ui.scrim.hidden = false;
  }

  function closeDrawer() {
    if (ui.app.dataset.drawer !== "open") return;
    delete ui.app.dataset.drawer;
    leave(ui.scrim, () => { if (ui.app.dataset.drawer !== "open") ui.scrim.hidden = true; });
  }

  return { label, restore, openDrawer, closeDrawer, toggle: () => setCollapsed(!collapsed()) };
}
