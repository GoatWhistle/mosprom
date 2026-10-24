const LAYERS = 8;
const LAYER_MS = 280;
const STAGGER_MS = 40;
const FADE_MS = 200;
const SCRAMBLE_MS = 520;
const EASE = "cubic-bezier(0.22, 1, 0.36, 1)";
const GLYPHS = "G01XYZEF;#%.2345";
const TARGETS = "h1, h2, h3, button, label, .section-title, .card-title, .status, .chat-title, .hint, .composer-hint";
const SURFACE = { dark: "#12130f", light: "#f6f5f2" };
const NOZZLE = "#ff8a3d";

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const animated = () => typeof document.body.animate === "function" && !reduced();

export async function layerSweep(target, apply) {
  if (!animated()) {
    apply();
    return;
  }
  const sweep = document.createElement("div");
  sweep.className = "layer-sweep";
  const bands = Array.from({ length: LAYERS }, (_, index) => {
    const band = document.createElement("div");
    const reverse = (LAYERS - 1 - index) % 2 === 1;
    band.className = reverse ? "layer-band rev" : "layer-band";
    band.style.background = SURFACE[target];
    band.style.boxShadow = (reverse ? -3 : 3) + "px 0 0 0 " + NOZZLE;
    sweep.append(band);
    return band;
  });
  document.body.append(sweep);
  let applied = false;
  try {
    await Promise.all(bands.map((band, index) => band.animate(
      { transform: [band.classList.contains("rev") ? "translateX(101%)" : "translateX(-101%)", "translateX(0)"] },
      { duration: LAYER_MS, delay: STAGGER_MS * (LAYERS - 1 - index), easing: EASE, fill: "both" }).finished));
    apply();
    applied = true;
    await sweep.animate({ opacity: [1, 0] }, { duration: FADE_MS, easing: EASE, fill: "both" }).finished;
  } finally {
    if (!applied) apply();
    sweep.remove();
  }
}

let stopScramble = null;

function scrambled(text, progress) {
  const shown = Math.floor(text.length * progress);
  return Array.from(text, (char, index) => index < shown || char.trim() === ""
    ? char : GLYPHS[Math.floor(Math.random() * GLYPHS.length)]).join("");
}

export function scrambleText() {
  if (stopScramble) stopScramble();
  if (!animated()) return;
  const jobs = [];
  for (const element of document.querySelectorAll(TARGETS)) {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.nodeValue || "";
      if (text.trim() && text.length <= 64 && !jobs.some((job) => job.node === node)) jobs.push({ node, text });
    }
  }
  const start = performance.now();
  let frame = 0;
  let handle = 0;
  const finish = () => {
    cancelAnimationFrame(handle);
    for (const job of jobs) job.node.nodeValue = job.text;
    stopScramble = null;
  };
  const tick = (now) => {
    const progress = Math.min((now - start) / SCRAMBLE_MS, 1);
    frame += 1;
    if (frame % 2 === 0) for (const job of jobs) job.node.nodeValue = scrambled(job.text, progress);
    if (progress < 1) handle = requestAnimationFrame(tick);
    else finish();
  };
  stopScramble = finish;
  for (const job of jobs) job.node.nodeValue = scrambled(job.text, 0);
  handle = requestAnimationFrame(tick);
  for (const paragraph of document.querySelectorAll(".empty p, .msg-assistant p")) {
    paragraph.animate({ opacity: [0, 1] }, { duration: 260, easing: EASE });
  }
}
