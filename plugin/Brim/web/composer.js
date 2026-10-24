import { action } from "./api.js";
import { chip, h } from "./dom.js";

const $ = (id) => document.getElementById(id);

export function renderComposer(ui, view, state, showError) {
  const t = view.t;
  if (view.draft_rev !== state.draftRev) {
    state.draftRev = view.draft_rev;
    if (document.activeElement !== ui.input || view.draft === "") ui.input.value = view.draft || "";
  }
  const asking = !!view.question && !view.busy;
  const confirming = !!view.confirmation && !view.busy;
  const placeholder = confirming ? t.placeholder_reject : asking ? t.placeholder_answer : t.placeholder;
  ui.input.placeholder = placeholder;
  ui.input.setAttribute("aria-label", placeholder);
  $("drop-text").textContent = t.drop_files;
  const attach = $("attach");
  attach.disabled = !!view.busy;
  attach.title = t.attach_hint;
  attach.setAttribute("aria-label", t.attach);
  $("send").hidden = !!view.run_active;
  syncSend(ui, view, state);
  $("send").setAttribute("aria-label", t.send);
  $("send").title = t.composer_hint;
  $("stop").hidden = !view.run_active;
  $("stop").disabled = !!view.stopping;
  $("stop").setAttribute("aria-label", t.stop);
  const chips = (view.attachments || []).map((item, index) => chip(item.name,
    () => action("removeAttachment", index).catch(showError), t.remove));
  ui.attachments.replaceChildren(...chips, ...state.uploading.map((name) => chip(name, null, null, true)));
  ui.attachments.hidden = !ui.attachments.children.length;
  const options = view.skill_options || [];
  ui.skill.hidden = options.length === 0;
  ui.skill.title = t.skill_hint;
  ui.skill.setAttribute("aria-label", t.skill_hint);
  ui.skill.replaceChildren(...options.map((item) => h("option", { value: item.name, text: item.title })));
  ui.skill.value = view.skill || "";
}

export function syncSend(ui, view, state) {
  const empty = !ui.input.value.trim() && !(view.attachments || []).length && !state.uploading.length;
  $("send").disabled = !!view.busy || empty;
}
