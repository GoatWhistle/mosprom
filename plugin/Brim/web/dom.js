import { icon } from "./icons.js";

const ALLOWED_TAGS = new Set(["A", "B", "BR", "CODE", "DIV", "EM", "FONT", "H1", "H2", "H3", "HR", "I", "LI", "OL", "P",
  "PRE", "S", "SPAN", "STRONG", "TABLE", "TBODY", "TD", "TH", "THEAD", "TR", "U", "UL", "BLOCKQUOTE", "DEL"]);
const ALLOWED_ATTRS = new Set(["href", "colspan", "rowspan"]);
const HEADING_STYLE = /font-weight\s*:\s*[6-9]00/i;

export function h(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [name, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (name === "class") node.className = value;
    else if (name === "text") node.textContent = value;
    else if (name.startsWith("on")) node.addEventListener(name.slice(2), value);
    else if (name in node && typeof value !== "string") node[name] = value;
    else node.setAttribute(name, value === true ? "" : value);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function cleanTree(root) {
  for (const node of Array.from(root.querySelectorAll("*"))) {
    if (!ALLOWED_TAGS.has(node.tagName)) {
      node.replaceWith(document.createTextNode(node.textContent));
      continue;
    }
    const heading = HEADING_STYLE.test(node.getAttribute("style") || "");
    for (const attr of Array.from(node.attributes)) {
      if (!ALLOWED_ATTRS.has(attr.name)) node.removeAttribute(attr.name);
    }
    if (heading) node.className = "rich-heading";
    if (node.tagName === "A") {
      if (!/^https?:\/\//i.test(node.getAttribute("href") || "")) node.removeAttribute("href");
      node.setAttribute("target", "_blank");
      node.setAttribute("rel", "noopener noreferrer");
    }
  }
}

export function richText(html) {
  const template = document.createElement("template");
  template.innerHTML = html || "";
  cleanTree(template.content);
  const box = h("div", { class: "rich" });
  box.append(template.content);
  return box;
}

export function extension(name) {
  const dot = (name || "").lastIndexOf(".");
  return dot >= 0 ? name.slice(dot + 1).toUpperCase() : "FILE";
}

export function chip(name, onRemove, label, uploading) {
  return h("span", { class: "chip" + (onRemove ? " chip-removable" : "") + (uploading ? " chip-uploading" : ""), title: name },
    h("span", { class: "chip-ext", text: extension(name) }),
    h("span", { class: "chip-name", text: name }),
    onRemove ? h("button", { class: "icon-button chip-remove", type: "button", "aria-label": label || name, onclick: onRemove },
      icon("close", "sm")) : null);
}

export function clock(seconds) {
  const total = Math.floor(seconds);
  const rest = total % 60;
  return Math.floor(total / 60) + ":" + (rest < 10 ? "0" : "") + rest;
}
