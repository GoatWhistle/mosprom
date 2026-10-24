import { h } from "./dom.js";
import { icon } from "./icons.js";

function place(host) {
  const indicator = host.querySelector(".segmented-indicator");
  const checked = host.querySelector('[aria-checked="true"]');
  if (!indicator || !checked || !host.clientWidth) return;
  const left = checked.offsetLeft;
  const right = host.clientWidth - checked.offsetLeft - checked.offsetWidth;
  indicator.style.clipPath = "inset(0 " + right + "px 0 " + left + "px round var(--radius-pill))";
  if (!indicator.dataset.ready) requestAnimationFrame(() => { indicator.dataset.ready = "true"; });
}

function step(host, delta, onPick) {
  const options = Array.from(host.querySelectorAll(".segmented-option"));
  const index = options.findIndex((node) => node.getAttribute("aria-checked") === "true");
  const next = options[(index + delta + options.length) % options.length];
  if (!next) return;
  next.focus();
  onPick(next.dataset.value);
}

export function renderSegmented(host, options, current, onPick) {
  const keys = options.map((option) => option.value).join("|");
  if (host.dataset.keys !== keys) {
    host.dataset.keys = keys;
    host.setAttribute("role", "radiogroup");
    host.replaceChildren(h("span", { class: "segmented-indicator", "aria-hidden": "true" }),
      ...options.map((option) => h("button", { class: "segmented-option", type: "button", role: "radio",
        "data-value": option.value })));
    host.onkeydown = (event) => {
      if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); step(host, 1, host.onpick); }
      if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); step(host, -1, host.onpick); }
    };
    if (typeof ResizeObserver === "function") new ResizeObserver(() => place(host)).observe(host);
  }
  host.onpick = onPick;
  const buttons = host.querySelectorAll(".segmented-option");
  options.forEach((option, index) => {
    const button = buttons[index];
    const checked = option.value === current;
    button.replaceChildren(...(option.icon ? [icon(option.icon, "sm")] : []), option.text);
    button.title = option.title || "";
    button.setAttribute("aria-checked", String(checked));
    button.tabIndex = checked ? 0 : -1;
    button.onclick = () => { if (!checked) onPick(option.value); };
  });
  place(host);
}
