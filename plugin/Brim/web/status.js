import { action } from "./api.js";
import { spinner } from "./brand.js";
import { clock, h } from "./dom.js";
import { icon } from "./icons.js";

const SLOW_THINKING_SECONDS = 60;
function stepLabel(activity, t) {
  return activity.step > 0 ? (t.activity_step || "") + " " + activity.step : "";
}

function activityBar(view, report, mark) {
  const activity = view.activity;
  if (!activity) return null;
  const t = view.t;
  const waiting = activity.kind === "confirm";
  const elapsed = activity.since ? Math.max(0, Date.now() / 1000 - activity.since) : 0;
  const slow = activity.kind === "thinking" && elapsed >= SLOW_THINKING_SECONDS;
  const progress = view.progress;
  const fraction = progress ? Math.max(0, Math.min(1, progress.fraction || 0)) : 0;
  return h("div", { class: "activity" + (waiting ? " activity-waiting" : "") },
    h("div", { class: "activity-head" },
      waiting ? h("span", { class: "status-slot" }, h("span", { class: "status-dot status-dot-attention" })) : mark || spinner("md"),
      h("span", { class: "activity-text", text: activity.text || "" }),
      waiting || !stepLabel(activity, t) ? null : h("span", { class: "tag", text: stepLabel(activity, t) }),
      waiting ? null : h("span", { class: "mono activity-meta" + (slow ? " activity-meta-slow" : ""),
        "data-since": activity.since || "", text: clock(elapsed) })),
    waiting ? null : h("div", { class: "progress" + (progress ? "" : " progress-indeterminate"), role: "progressbar",
      "aria-valuemin": "0", "aria-valuemax": "100", "aria-valuenow": progress ? String(Math.round(fraction * 100)) : null },
      h("div", { class: "progress-fill", style: progress ? "--progress:" + fraction.toFixed(3) : null })),
    progress && progress.stage ? h("div", { class: "activity-stage" }, h("span", { text: progress.stage }),
      h("span", { class: "mono", text: Math.round(fraction * 100) + "%" })) : null,
    slow ? h("div", { class: "activity-slow" }, h("span", { text: t.slow_hint || "" }),
      h("button", { class: "button button-danger button-compact", type: "button", text: t.stop,
        onclick: () => action("stop").catch(report) })) : null);
}

export function renderStatus(host, view, report) {
  const t = view.t;
  const run = (name) => () => action(name).catch(report);
  const shown = new Set(Array.from(host.children, (node) => node.classList[0]));
  const mark = host.querySelector(".activity-head > .spinner");
  const nodes = [
    activityBar(view, report, mark),
    view.notice ? h("button", { class: "notice", type: "button", title: t.close, onclick: run("dismissNotice") },
      h("span", { class: "notice-text", text: view.notice }), icon("close", "sm")) : null,
    view.switch_prompt ? h("div", { class: "card switch-prompt" },
      h("div", { class: "card-text", text: t.switch_busy_title + ". " + t.switch_busy_body }),
      h("div", { class: "card-actions" },
        h("button", { class: "button button-secondary button-compact", type: "button", text: t.switch_wait, onclick: run("cancelSwitch") }),
        h("button", { class: "button button-danger button-compact", type: "button", text: t.switch_stop, onclick: run("stopAndSwitch") }))) : null,
    view.can_retry_switch || view.workspace_blocked ? h("div", { class: "cluster" },
      view.can_retry_switch ? h("button", { class: "button button-compact", type: "button", text: t.retry, onclick: run("retrySwitch") }) : null,
      view.workspace_blocked ? h("button", { class: "button button-compact", type: "button", text: t.recover, disabled: !!view.switching,
        onclick: run("recoverWorkspace") }) : null) : null,
  ].filter(Boolean);
  for (const node of nodes) if (shown.has(node.classList[0])) node.dataset.static = "true";
  host.replaceChildren(...nodes);
}

export function tickClocks(host) {
  for (const node of host.querySelectorAll(".activity-meta[data-since]")) {
    const since = parseFloat(node.getAttribute("data-since"));
    if (since) node.textContent = clock(Math.max(0, Date.now() / 1000 - since));
  }
}
