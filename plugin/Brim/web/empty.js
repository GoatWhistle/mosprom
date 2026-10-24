import { h } from "./dom.js";
import { icon } from "./icons.js";

const SUGGESTIONS = [["calibrate", "target"], ["part", "scene"], ["material", "layers"], ["defect", "search"]];

export function renderEmpty(host, view, onPick) {
  const t = view.t;
  const language = view.language;
  if (host.dataset.language === language) return;
  host.dataset.language = language;
  host.replaceChildren(...SUGGESTIONS.map(([name, glyph], index) => {
    const text = t["suggest_" + name + "_text"];
    return h("button", { class: "suggestion", type: "button", title: text, style: "--i:" + index, onclick: () => onPick(text) },
      icon(glyph, "sm"), h("span", { text: t["suggest_" + name + "_title"] }));
  }));
}
