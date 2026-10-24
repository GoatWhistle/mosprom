import { buildEntry } from "./entries.js";
import { readMs } from "./motion.js";

const INTERACTIVE = { question: "question", confirmation: "confirmation" };
const STAGGERED = 10;
const END_SLACK = 24;

export function createTimeline(ui, state, ctx) {
  let entering = 0;

  function payloadOf(entry) {
    const view = state.view;
    const field = INTERACTIVE[entry.kind];
    const active = field && view[field] && view[field].call_id === entry.call_id && !view.busy;
    return JSON.stringify(entry) + (active ? "|active" : "");
  }

  function atEnd() {
    const node = ui.timeline;
    return node.scrollHeight - node.scrollTop - node.clientHeight < END_SLACK;
  }

  function scrollToEnd() {
    ui.timeline.scrollTop = state.view && (state.view.entries || []).length ? ui.timeline.scrollHeight : 0;
    state.followEnd = true;
    ui.jump.hidden = true;
  }

  function enter(nodes) {
    nodes.slice(-STAGGERED).forEach((node, index) => node.style.setProperty("--i", String(index)));
    ui.entries.classList.add("entries-enter");
    clearTimeout(entering);
    entering = setTimeout(() => ui.entries.classList.remove("entries-enter"),
      readMs("--dur-slow") + readMs("--stagger") * STAGGERED);
  }

  function render() {
    const entries = state.view.entries || [];
    const switched = state.view.conversation_id !== state.conversation;
    const first = state.conversation === "\u0000";
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
      const payload = payloadOf(entries[index]);
      if (state.rendered[index].payload !== payload) {
        nodes[index].replaceWith(buildEntry(entries[index], ctx));
        state.rendered[index] = { key: entries[index].key, payload };
      }
    }
    for (const node of nodes.slice(keep)) node.remove();
    state.rendered.length = keep;
    const added = [];
    for (let index = keep; index < entries.length; index++) {
      const node = buildEntry(entries[index], ctx);
      if (!switched) node.classList.add("entry-fresh");
      ui.entries.append(node);
      added.push(node);
      state.rendered.push({ key: entries[index].key, payload: payloadOf(entries[index]) });
    }
    if (switched && !first) enter(added);
    ui.empty.hidden = entries.length > 0;
    ui.timeline.dataset.stale = state.view.switching ? "true" : "false";
    if (follow) scrollToEnd();
    else if (entries.length > keep) ui.jump.hidden = false;
  }

  function rebuild() {
    state.rendered = [];
    render();
  }

  return { render, rebuild, atEnd, scrollToEnd };
}
