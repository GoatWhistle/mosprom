const PART = "M62 54H102A8 8 0 0 1 110 62V102A8 8 0 0 1 102 110H62A8 8 0 0 1 54 102V62A8 8 0 0 1 62 54Z";
const RINGS = [
  "M62 36H102A26 26 0 0 1 128 62V102A26 26 0 0 1 102 128H62A26 26 0 0 1 36 102V62A26 26 0 0 1 62 36Z"
    + "M62 44H102A18 18 0 0 1 120 62V102A18 18 0 0 1 102 120H62A18 18 0 0 1 44 102V62A18 18 0 0 1 62 44Z",
  "M62 18H102A44 44 0 0 1 146 62V102A44 44 0 0 1 102 146H62A44 44 0 0 1 18 102V62A44 44 0 0 1 62 18Z"
    + "M62 26H102A36 36 0 0 1 138 62V102A36 36 0 0 1 102 138H62A36 36 0 0 1 26 102V62A36 36 0 0 1 62 26Z",
  "M62 0H102A62 62 0 0 1 164 62V102A62 62 0 0 1 102 164H62A62 62 0 0 1 0 102V62A62 62 0 0 1 62 0Z"
    + "M62 8H102A54 54 0 0 1 156 62V102A54 54 0 0 1 102 156H62A54 54 0 0 1 8 102V62A54 54 0 0 1 62 8Z",
];
const WORD_STROKE = "M6.5 0V90M81.5 30V90M81.5 63C81.5 45 90.5 36.5 104 36.5H117M131.5 30V90M156.5 90V56C156.5 44 164 "
  + "36.5 175 36.5C186 36.5 193.5 44 193.5 56V90M193.5 56C193.5 44 201 36.5 212 36.5C223 36.5 230.5 44 230.5 56V90";
const WORD_BOWL = "M26.5 36.5H36.5A20 20 0 0 1 56.5 56.5V63.5A20 20 0 0 1 36.5 83.5H26.5A20 20 0 0 1 6.5 63.5V56.5A20 20 0 0 1 "
  + "26.5 36.5Z";
const WORD_DOT = "M125 0H138V13H125Z";

function parse(markup) {
  const template = document.createElement("template");
  template.innerHTML = markup;
  return template.content.firstElementChild;
}

function markMarkup(motion) {
  const rings = RINGS.map((path, index) => '<path class="brand-ring ' + (index === RINGS.length - 1 ? "brand-accent" : "brand-base")
    + '" style="--ring-index:' + (index + 1) + '" fill-rule="evenodd" d="' + path + '"/>').join("");
  return '<svg class="brand-mark' + (motion ? " brand-" + motion : "") + '" viewBox="0 0 164 164" aria-hidden="true" focusable="false">'
    + '<path class="brand-part brand-base" d="' + PART + '"/>' + rings + "</svg>";
}

function wordMarkup() {
  return '<svg class="brand-word" viewBox="0 0 237 90" aria-hidden="true" focusable="false">'
    + '<path class="brand-word-stroke" stroke-width="13" d="' + WORD_STROKE + " " + WORD_BOWL + '"/>'
    + '<path class="brand-word-dot" d="' + WORD_DOT + '"/></svg>';
}

export function brandMark(motion) {
  return parse(markMarkup(motion));
}

export function brandLockup(motion) {
  return parse('<span class="brand-lockup" role="img" aria-label="Brim">' + markMarkup(motion) + wordMarkup() + "</span>");
}

export function spinner(size) {
  return parse('<span class="spinner' + (size === "md" ? " spinner-md" : "") + '" aria-hidden="true">' + markMarkup("loop") + "</span>");
}
