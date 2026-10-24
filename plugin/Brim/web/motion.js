const LAYERS = 8;
const GLYPHS = "G01XYZEF;#%.2345";
const TARGETS = "h1, h2, h3, button, label, .sidebar-title, .card-eyebrow, .header-status, .card-hint, .composer-hint, "
  + ".activity-text, .empty-state-text, [data-scramble]";
const MAX_LENGTH = 64;
const MAX_NODES = 80;
const SHUFFLE_FRAMES = 2;
const DURATION = /^(-?\d*\.?\d+)(ms|s)$/;
const FRAME_MS = 16;

const reduced = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const animated = () => typeof document.body.animate === "function" && !reduced();

function token(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function motionMs(name) {
  const match = DURATION.exec(token(name));
  if (!match) return 0;
  return match[2] === "s" ? Number(match[1]) * 1000 : Number(match[1]);
}

function easing(name) {
  return token(name) || "linear";
}

export function readMs(name) {
  return motionMs(name);
}

function bezier(value) {
  const match = /cubic-bezier\(([^)]+)\)/.exec(value);
  if (!match) return (x) => x;
  const [x1, y1, x2, y2] = match[1].split(",").map(Number);
  const curve = (a, b, t) => 3 * a * (1 - t) * (1 - t) * t + 3 * b * (1 - t) * t * t + t * t * t;
  return (x) => {
    let low = 0;
    let high = 1;
    for (let index = 0; index < 20; index++) {
      const middle = (low + high) / 2;
      if (curve(x1, x2, middle) < x) low = middle;
      else high = middle;
    }
    return curve(y1, y2, (low + high) / 2);
  };
}

function layerClip(widths) {
  const band = 100 / LAYERS;
  const left = [];
  const right = [];
  widths.forEach((width, index) => {
    const bottom = (100 - index * band).toFixed(2);
    const top = (100 - (index + 1) * band).toFixed(2);
    const fromLeft = index % 2 === 0;
    const start = (fromLeft ? 0 : 100 - width * 100).toFixed(2);
    const end = (fromLeft ? width * 100 : 100).toFixed(2);
    left.push(start + "% " + bottom + "%", start + "% " + top + "%");
    right.unshift(end + "% " + top + "%", end + "% " + bottom + "%");
  });
  return "polygon(" + left.concat(right).join(", ") + ")";
}

const framesCache = new Map();

function layerFrames(duration, stagger, curve) {
  const key = duration + "|" + stagger + "|" + curve;
  if (!framesCache.has(key)) framesCache.set(key, buildFrames(duration, stagger, bezier(curve)));
  return framesCache.get(key);
}

function buildFrames(duration, stagger, ease) {
  const total = duration + stagger * (LAYERS - 1);
  const count = Math.max(2, Math.round(total / FRAME_MS));
  return Array.from({ length: count + 1 }, (_, frame) => {
    const time = (frame / count) * total;
    return { clipPath: layerClip(Array.from({ length: LAYERS }, (__, index) =>
      ease(Math.max(0, Math.min(1, (time - index * stagger) / duration))))) };
  });
}

export async function switchTheme(target, apply) {
  if (!animated()) {
    apply();
    return;
  }
  if (typeof document.startViewTransition !== "function") {
    await layerSweep(target, apply);
    return;
  }
  const root = document.documentElement;
  const duration = motionMs("--dur-layer");
  const stagger = motionMs("--stagger-layer");
  layerFrames(duration, stagger, token("--ease-wave"));
  try {
    const transition = document.startViewTransition(() => {
      root.dataset.switching = "true";
      apply();
    });
    await transition.ready;
    root.animate(layerFrames(duration, stagger, token("--ease-wave")),
      { duration: duration + stagger * (LAYERS - 1), easing: "linear", fill: "both", pseudoElement: "::view-transition-new(root)" });
    await transition.finished;
  } catch (error) {
    if (root.dataset.theme !== target) apply();
  } finally {
    delete root.dataset.switching;
  }
}

export function leave(element, done) {
  if (!animated()) {
    done();
    return;
  }
  element.dataset.leaving = "true";
  setTimeout(() => {
    delete element.dataset.leaving;
    done();
  }, motionMs("--dur-exit"));
}

export function warmMotion() {
  layerFrames(motionMs("--dur-layer"), motionMs("--stagger-layer"), token("--ease-wave"));
}

export async function layerSweep(target, apply) {
  if (!animated()) {
    apply();
    return;
  }
  const sweep = document.createElement("div");
  sweep.className = "layer-sweep layer-sweep-" + target;
  sweep.setAttribute("aria-hidden", "true");
  const bands = Array.from({ length: LAYERS }, (_, index) => {
    const band = document.createElement("div");
    band.className = index % 2 === LAYERS % 2 ? "layer-band layer-band-reverse" : "layer-band";
    sweep.append(band);
    return band;
  });
  document.body.append(sweep);
  const duration = motionMs("--dur-layer");
  const stagger = motionMs("--stagger-layer");
  const wave = easing("--ease-wave");
  let applied = false;
  try {
    await Promise.all(bands.map((band, index) => band.animate(
      { transform: [band.classList.contains("layer-band-reverse") ? "translateX(101%)" : "translateX(-101%)", "translateX(0)"] },
      { duration, easing: wave, delay: stagger * (LAYERS - 1 - index), fill: "both" }).finished));
    apply();
    applied = true;
    await sweep.animate({ opacity: [1, 0] }, { duration: motionMs("--dur-base"), easing: easing("--ease-out"), fill: "both" }).finished;
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

function collect() {
  const seen = new Set();
  for (const element of document.body.querySelectorAll(TARGETS)) {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.nodeValue || "";
      if (text.trim() && text.length <= MAX_LENGTH) seen.add(node);
    }
  }
  return Array.from(seen).slice(0, MAX_NODES).map((node) => ({ node, text: node.nodeValue || "" }));
}

export function scrambleText() {
  if (stopScramble) stopScramble();
  if (!animated()) return;
  const jobs = collect();
  const duration = motionMs("--dur-scramble");
  const start = performance.now();
  let frame = 0;
  let handle = 0;
  const finish = () => {
    cancelAnimationFrame(handle);
    for (const job of jobs) job.node.nodeValue = job.text;
    stopScramble = null;
  };
  const tick = (now) => {
    const progress = Math.min((now - start) / duration, 1);
    frame += 1;
    if (frame % SHUFFLE_FRAMES === 0) for (const job of jobs) job.node.nodeValue = scrambled(job.text, progress);
    if (progress < 1) handle = requestAnimationFrame(tick);
    else finish();
  };
  stopScramble = finish;
  for (const job of jobs) job.node.nodeValue = scrambled(job.text, 0);
  handle = requestAnimationFrame(tick);
}
