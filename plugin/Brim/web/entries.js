import { downloadUrl } from "./api.js";
import { chip, h, richText } from "./dom.js";

function bubble(entry, ctx) {
  const mine = entry.kind === "user";
  const chips = (entry.attachments || []).map((name) => chip(name));
  return h("div", { class: "msg " + (mine ? "msg-user" : "msg-agent") },
    h("div", { class: "msg-body" },
      mine ? h("div", { class: "msg-text", text: entry.text || "" }) : richText(entry.html || ""),
      chips.length ? h("div", { class: "chips" }, chips) : null));
}

function toolLabel(entry, t) {
  const name = entry.server === "brim" ? (t["tool_" + entry.tool] || entry.tool) : entry.tool;
  const server = entry.server && entry.server !== "brim" ? entry.server + " · " : "";
  return server + name + " · " + (t["tool_" + entry.status] || entry.status);
}

function toolRow(entry, ctx) {
  const failed = entry.status === "failed" || entry.status === "rejected";
  const running = entry.status === "running";
  const mark = running ? h("span", { class: "spinner small", "aria-hidden": "true" })
    : h("span", { class: "tool-mark", text: failed ? "✕" : entry.status === "ok" ? "✓" : "•" });
  return h("div", { class: "tool tool-" + entry.status + (failed ? " tool-failed" : "") },
    h("div", { class: "tool-head" }, mark, h("span", { class: "tool-label", text: toolLabel(entry, ctx.t) })),
    running ? h("div", { class: "dashes", "aria-hidden": "true" }) : null,
    entry.detail ? h("div", { class: "tool-detail mono", text: entry.detail }) : null);
}

function toolGroup(entry, ctx) {
  const open = ctx.isExpanded(entry.key);
  const items = entry.items || [];
  return h("div", { class: "tool-group" + (open ? " open" : "") },
    h("button", { class: "tool-group-head", type: "button", "aria-expanded": String(open),
      onclick: () => ctx.toggle(entry.key) },
      h("span", { class: "dot ok" }),
      h("span", { text: (ctx.t.agent_actions || "") + " · " + items.length }),
      h("span", { class: "caret", text: "˅" })),
    open ? h("div", { class: "tool-group-items" }, items.map((item) => toolRow(item, ctx))) : null);
}

function questionCard(entry, ctx) {
  const view = ctx.view;
  const active = !!view.question && view.question.call_id === entry.call_id && !view.busy;
  const questions = entry.questions || [];
  return h("div", { class: "card card-question" },
    h("div", { class: "card-title", text: ctx.t.question || "" }),
    questions.map((question, index) => h("div", { class: "question" },
      h("div", { class: "question-text", text: (questions.length > 1 ? index + 1 + ". " : "") + question.text }),
      active && (question.options || []).length ? h("div", { class: "row wrap" },
        question.options.map((option) => h("button", { class: "btn", type: "button", text: option,
          onclick: () => ctx.pickOption(questions.length > 1 ? index + 1 + ". " + option : option) }))) : null)),
    active ? h("div", { class: "hint", text: ctx.t.answer_hint || "" }) : null,
    entry.answer ? h("div", { class: "muted", text: (ctx.t.answered || "") + ": " + entry.answer }) : null);
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
  return h("div", { class: "card card-confirm" + (active ? " active" : "") },
    h("div", { class: "card-title accent", text: (t.confirmation || "") +
      (entry.server && entry.server !== "brim" ? " · " + entry.server : "") }),
    entry.explanation ? h("div", { class: "card-text", text: entry.explanation }) : null,
    h("div", { class: "ops" }, (entry.items || []).map((item) => h("div", { class: "op" },
      h("span", { class: "op-kind", text: t["op_" + item.kind] || item.kind }),
      h("div", { class: "op-body" },
        h("div", { class: "mono op-detail", text: operationDetail(item) }),
        item.risky ? h("div", { class: "op-risk", text: (t["risk_" + item.reason] || item.reason) +
          (item.limits ? " " + item.limits : "") }) : null)))),
    active ? h("div", { class: "row wrap" },
      h("button", { class: "btn primary", type: "button", text: t.apply || "", onclick: () => ctx.confirm("accept") }),
      h("button", { class: "btn danger", type: "button", text: t.reject || "", onclick: () => ctx.confirm("reject") })) : null,
    active ? h("div", { class: "hint", text: t.confirm_comment_hint || "" }) : null);
}

function duration(seconds, t) {
  if (seconds === undefined || seconds === null) return "—";
  return Math.floor(seconds / 3600) + " " + t.hours + " " + Math.round((seconds % 3600) / 60) + " " + t.minutes;
}

function weight(values, t) {
  if (!values || !values.length) return "—";
  return values.reduce((sum, value) => sum + value, 0).toFixed(1) + " " + t.grams;
}

function resultCard(entry, ctx) {
  const t = ctx.t;
  const result = entry.result || {};
  const summary = result.summary || {};
  const files = result.files || {};
  const stat = (value, label) => h("div", { class: "stat" }, h("div", { class: "stat-value", text: value }),
    h("div", { class: "stat-label", text: label }));
  return h("div", { class: "card card-result" },
    h("div", { class: "card-title", text: t.result || "" }),
    h("div", { class: "stats" }, stat(duration(summary.print_time_seconds, t), t.print_time || ""),
      stat(weight(summary.material_weight_g, t), t.material || "")),
    ["gcode", "3mf"].filter((kind) => files[kind]).map((kind) => h("div", { class: "file-row" },
      h("span", { class: "mono file-path", text: files[kind] }),
      h("a", { class: "btn small", href: downloadUrl(files[kind]), download: "", text: (t.download || "") + " " + kind.toUpperCase() }))),
    h("div", { class: "row wrap" },
      h("button", { class: "btn primary", type: "button", text: t.open_folder || "", onclick: () => ctx.openFolder(result.folder || "") })));
}

function errorRow(entry, ctx) {
  return h("div", { class: "card card-error", role: "alert", text: (ctx.t.error || "") + ": " + (entry.text || "") });
}

const BUILDERS = { user: bubble, assistant: bubble, tool: toolRow, tool_group: toolGroup, question: questionCard,
  confirmation: confirmCard, result: resultCard };

export function buildEntry(entry, ctx) {
  return (BUILDERS[entry.kind] || errorRow)(entry, ctx);
}
