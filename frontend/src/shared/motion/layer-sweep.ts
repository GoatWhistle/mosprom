import { flushSync } from "react-dom"
import { motionMs, readEasing } from "./css-tokens"
import { prefersReducedMotion } from "./use-reduced-motion"

export type SweepTarget = "light" | "dark"

const LAYERS = 8

function buildSweep(target: SweepTarget): { sweep: HTMLElement; bands: HTMLElement[] } {
  const sweep = document.createElement("div")
  sweep.className = `layer-sweep layer-sweep-${target}`
  sweep.setAttribute("aria-hidden", "true")
  const bands = Array.from({ length: LAYERS }, (_, index) => {
    const band = document.createElement("div")
    band.className = index % 2 === LAYERS % 2 ? "layer-band layer-band-reverse" : "layer-band"
    sweep.append(band)
    return band
  })
  document.body.append(sweep)
  return { sweep, bands }
}

export async function withLayerSweep(target: SweepTarget, change: () => void): Promise<void> {
  if (prefersReducedMotion() || typeof document.body.animate !== "function") {
    change()
    return
  }
  const { sweep, bands } = buildSweep(target)
  const duration = motionMs("--dur-layer")
  const stagger = motionMs("--stagger-layer")
  const easing = readEasing("--ease-wave")
  let changed = false
  try {
    await Promise.all(
      bands.map((band, index) => {
        const from = band.classList.contains("layer-band-reverse") ? "101%" : "-101%"
        return band.animate(
          { transform: [`translateX(${from})`, "translateX(0)"] },
          { duration, easing, delay: stagger * (LAYERS - 1 - index), fill: "both" },
        ).finished
      }),
    )
    flushSync(change)
    changed = true
    await sweep.animate(
      { opacity: [1, 0] },
      { duration: motionMs("--dur-base"), easing: readEasing("--ease-out"), fill: "both" },
    ).finished
  } finally {
    if (!changed) flushSync(change)
    sweep.remove()
  }
}
