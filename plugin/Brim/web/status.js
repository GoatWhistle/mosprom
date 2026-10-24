import { action } from "./api.js";
import { clock, h } from "./dom.js";

const SLOW_THINKING_SECONDS = 60;

function activityBar(view, report) {
  const activity = view.activity;
  if (!activity) return null;
  const t = view.t;
  const waiting = activity.kind === "confirm";
  const elapsed = activity.since ? Math.max(0, Date.now() / 1000 - activity.since) : 0;
  const slow = activity.kind === "thinking" && elapsed >= SLOW_THINKING_SECONDS;
  const progress = view.progress;
  const fraction = progress ? Math.max(0, Math.min(1, progress.fraction || 0)) : 0;
  return h("div", { class: "activity" + (waiting ? " waiting" : "") },
    h("div", { class: "activity-head" },
      waiting ? h("span", { class: "pulse", "aria-hidden": "true" }) : h("span", { class: "spinner", "aria-hidden": "true" }),
      h("span", { class: "activity-text", text: activity.text || "" }),
      waiting ? null : h("span", { class: "activity-meta mono" + (slow ? " accent" : ""), "data-since": activity.since || "",
        "data-step": activity.step > 0 ? (t.activity_step || "") + " " + activity.step + "  ·  " : "",
        text: (activity.step > 0 ? (t.activity_step || "") + " " + activity.step + "  ·  " : "") + clock(elapsed) })),
    waiting ? null : h("div", { class: "track" + (progress ? "" : " indeterminate") },
      h("div", { class: "fill", style: progress ? "width:" + (fraction * 100).toFixed(1) + "%" : null })),
    progress && progress.stage ? h("div", { class: "muted small", text: progress.stage + "  " + Math.round(fraction * 100) + "%" }) : null,
    slow ? h("div", { class: "row slow" }, h("span", { class: "accent small", text: t.slow_hint || "" }),
      h("button", { class: "btn danger", type: "button", text: t.stop, onclick: () => action("stop").catch(report) })) : null);
}

export function renderStatus(host, view, report) {
  const t = view.t;
  const run = (name) => () => action(name).catch(report);
  host.replaceChildren(...[
    activityBar(view, report),
    view.notice ? h("button", { class: "notice", type: "button", text: view.notice, onclick: run("dismissNotice") }) : null,
    view.switch_prompt ? h("div", { class: "switch" },
      h("div", { text: t.switch_busy_title + ". " + t.switch_busy_body }),
      h("div", { class: "row wrap" },
        h("button", { class: "btn", type: "button", text: t.switch_wait, onclick: run("cancelSwitch") }),
        h("button", { class: "btn danger", type: "button", text: t.switch_stop, onclick: run("stopAndSwitch") }))) : null,
    view.can_retry_switch || view.workspace_blocked ? h("div", { class: "row wrap" },
      view.can_retry_switch ? h("button", { class: "btn primary", type: "button", text: t.retry, onclick: run("retrySwitch") }) : null,
      view.workspace_blocked ? h("button", { class: "btn primary", type: "button", text: t.recover, disabled: !!view.switching,
        onclick: run("recoverWorkspace") }) : null) : null,
  ].filter(Boolean));
}

export function tickClocks(host) {
  for (const node of host.querySelectorAll(".activity-meta[data-since]")) {
    const since = parseFloat(node.getAttribute("data-since"));
    if (since) node.textContent = node.getAttribute("data-step") + clock(Math.max(0, Date.now() / 1000 - since));
  }
}
