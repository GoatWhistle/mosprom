import { downloadUrl } from "./api.js";
import { brandMark, spinner } from "./brand.js";
import { chip, h, richText } from "./dom.js";
import { icon } from "./icons.js";

const TOOL_ICONS = { ok: "check", failed: "close", rejected: "close", skipped: "minus" };

function bubble(entry) {
  const mine = entry.kind === "user";
  const chips = (entry.attachments || []).map((name) => chip(name));
  const body = h("div", { class: "message-body" },
    mine ? (entry.text ? h("div", { class: "message-text", text: entry.text }) : null) : richText(entry.html || ""),
    chips.length ? h("div", { class: "chips" }, chips) : null);
  return h("div", { class: "message " + (mine ? "message-user" : "message-agent") }, mine ? null : brandMark(), body);
}

function travel() {
  const template = document.createElement("template");
  template.innerHTML = '<svg class="travel" aria-hidden="true" focusable="false" preserveAspectRatio="none">'
    + '<line class="travel-line" x1="0" y1="50%" x2="100%" y2="50%"/></svg>';
  return template.content.firstElementChild;
}

function toolRow(entry, ctx) {
  const t = ctx.t;
  const failed = entry.status === "failed" || entry.status === "rejected";
  const running = entry.status === "running";
  const name = entry.server === "brim" ? (t["tool_" + entry.tool] || entry.tool) : entry.tool;
  const server = entry.server && entry.server !== "brim" ? entry.server : "";
  return h("div", { class: "tool tool-" + (failed ? "failed" : entry.status) },
    h("div", { class: "tool-head" },
      running ? spinner() : icon(TOOL_ICONS[entry.status] || "pending", "sm"),
      server ? h("span", { class: "tag", text: server }) : null,
      h("span", { class: "tool-name" + (server ? " tool-name-code" : ""), text: name }),
      entry.status === "ok" ? null : h("span", { class: "tool-state", text: t["tool_" + entry.status] || entry.status })),
    running ? travel() : null,
    entry.detail ? h("div", { class: "tool-detail", text: entry.detail }) : null);
}

function toolGroup(entry, ctx) {
  const open = ctx.isExpanded(entry.key);
  const items = entry.items || [];
  const list = h("div", { class: "tool-group-items", inert: !open }, items.map((item) => toolRow(item, ctx)));
  const group = h("div", { class: "tool-group", "data-open": String(open) });
  const head = h("button", { class: "tool-group-head", type: "button", "aria-expanded": String(open), onclick: () => {
    const next = group.dataset.open !== "true";
    ctx.setExpanded(entry.key, next);
    group.dataset.open = String(next);
    head.setAttribute("aria-expanded", String(next));
    list.inert = !next;
  } },
  icon("check", "sm"),
  h("span", { text: ctx.t.agent_actions || "" }),
  h("span", { class: "tag", text: String(items.length) }),
  h("span", { class: "tool-group-caret" }, icon("chevron", "sm")));
  group.append(head, h("div", { class: "tool-group-body" }, list));
  return group;
}

function eyebrow(text, action, tag) {
  const label = h("div", { class: "card-eyebrow" }, h("span", { text }), tag ? h("span", { class: "tag", text: tag }) : null);
  return action ? h("div", { class: "card-header" }, label, action) : label;
}

function questionCard(entry, ctx) {
  const view = ctx.view;
  const active = !!view.question && view.question.call_id === entry.call_id && !view.busy;
  const questions = entry.questions || [];
  return h("div", { class: "card" + (active ? " card-active" : "") },
    eyebrow(ctx.t.question || ""),
    questions.map((question, index) => h("div", { class: "question" },
      h("div", { class: "card-text", text: (questions.length > 1 ? index + 1 + ". " : "") + question.text }),
      active && (question.options || []).length ? h("div", { class: "card-actions" },
        question.options.map((option) => h("button", { class: "button button-secondary button-compact", type: "button",
          text: option, onclick: () => ctx.pickOption(questions.length > 1 ? index + 1 + ". " + option : option, questions.length === 1) }))) : null)),
    entry.answer ? h("div", { class: "answered" }, h("span", { class: "answered-label", text: ctx.t.answered || "" }),
      h("span", { class: "answered-value", text: entry.answer })) : null);
}

function operationDetail(item) {
  if (item.kind === "external") return item.target + "\n" + item.detail;
  if (item.target) return item.target + ": " + item.detail;
  return item.detail || "—";
}

function confirmCard(entry, ctx) {
  const view = ctx.view;
  const t = ctx.t;
  const active = !!view.confirmation && view.confirmation.call_id === entry.call_id && !view.busy;
  return h("div", { class: "card" + (active ? " card-active" : "") },
    eyebrow(t.confirmation || "", null, entry.server && entry.server !== "brim" ? entry.server : null),
    entry.explanation ? h("div", { class: "card-text", text: entry.explanation }) : null,
    h("div", { class: "ops" }, (entry.items || []).map((item) => h("div", { class: "op" },
      h("span", { class: "op-kind", text: t["op_" + item.kind] || item.kind }),
      h("div", { class: "op-body" },
        h("div", { class: "op-detail", text: operationDetail(item) }),
        item.risky ? h("div", { class: "op-risk" }, icon("alert", "sm"), h("span", { text: (t["risk_" + item.reason] || item.reason)
          + (item.limits ? " " + item.limits : "") })) : null)))),
    active ? h("div", { class: "card-actions" },
      h("button", { class: "button button-compact", type: "button", text: t.apply || "", onclick: () => ctx.confirm("accept") }),
      h("button", { class: "button button-danger button-compact", type: "button", text: t.reject || "",
        onclick: () => ctx.confirm("reject") })) : null,
    null);
}

function duration(seconds, t) {
  if (seconds === undefined || seconds === null) return null;
  return Math.floor(seconds / 3600) + " " + t.hours + " " + Math.round((seconds % 3600) / 60) + " " + t.minutes;
}

function weight(values, t) {
  if (!values || !values.length) return null;
  return values.reduce((sum, value) => sum + value, 0).toFixed(1) + " " + t.grams;
}

function fileRow(path, kind, t) {
  const name = path.split(/[\\/]/).pop();
  return h("div", { class: "file" },
    icon("file"),
    h("div", { class: "file-text" }, h("span", { class: "file-name", text: name }),
      h("span", { class: "mono file-path", text: path.slice(0, path.length - name.length) })),
    h("a", { class: "button button-secondary button-compact", href: downloadUrl(path), download: "" },
      icon("download", "sm"), (t.download || "") + " " + kind.toUpperCase()));
}

function resultCard(entry, ctx) {
  const t = ctx.t;
  const result = entry.result || {};
  const summary = result.summary || {};
  const files = result.files || {};
  const kinds = ["gcode", "3mf"].filter((kind) => files[kind]);
  const stat = (value, label) => value === null ? null : h("div", { class: "stat" }, h("div", { class: "stat-value", text: value }),
    h("div", { class: "stat-label", text: label }));
  const stats = [stat(duration(summary.print_time_seconds, t), t.print_time || ""),
    stat(weight(summary.material_weight_g, t), t.material || "")].filter(Boolean);
  return h("div", { class: "card" },
    eyebrow(t.result || "", h("button", { class: "button button-ghost button-compact", type: "button",
      onclick: () => ctx.openFolder(result.folder || "") }, icon("folder", "sm"), t.open_folder || "")),
    stats.length ? h("div", { class: "stats" }, stats) : null,
    kinds.length ? h("div", { class: "file-list" }, kinds.map((kind) => fileRow(files[kind], kind, t))) : null);
}

function errorRow(entry, ctx) {
  return h("div", { class: "card card-danger", role: "alert" },
    h("div", { class: "card-alert" }, icon("alert"), h("div", { class: "card-text", text: (ctx.t.error || "") + ": " + (entry.text || "") })));
}

const BUILDERS = { user: bubble, assistant: bubble, tool: toolRow, tool_group: toolGroup, question: questionCard,
  confirmation: confirmCard, result: resultCard };

export function buildEntry(entry, ctx) {
  return (BUILDERS[entry.kind] || errorRow)(entry, ctx);
}
