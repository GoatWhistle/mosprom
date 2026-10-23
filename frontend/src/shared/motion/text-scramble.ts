import { flushSync } from "react-dom"
import { motionMs, readEasing } from "./css-tokens"
import { prefersReducedMotion } from "./use-reduced-motion"

const GLYPHS = "G01XYZEF;#%.2345"
const TARGETS = "h1, h2, h3, legend, button, label, dt, th, [data-scramble]"
const MAX_LENGTH = 48
const MAX_NODES = 60
const SHUFFLE_FRAMES = 2

interface Job {
  readonly node: Text
  readonly text: string
}

let stopRunning: (() => void) | null = null

function collect(): Job[] {
  const seen = new Set<Text>()
  for (const element of document.body.querySelectorAll(TARGETS)) {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT)
    for (let node = walker.nextNode(); node !== null; node = walker.nextNode()) {
      const text = node.nodeValue ?? ""
      if (text.trim() !== "" && text.length <= MAX_LENGTH) seen.add(node as Text)
    }
  }
  return [...seen].slice(0, MAX_NODES).map((node) => ({ node, text: node.nodeValue ?? "" }))
}

function scrambled(text: string, progress: number): string {
  const shown = Math.floor(text.length * progress)
  return [...text]
    .map((char, index) =>
      index < shown || char.trim() === ""
        ? char
        : (GLYPHS[Math.floor(Math.random() * GLYPHS.length)] ?? char),
    )
    .join("")
}

function scramble(jobs: readonly Job[]): void {
  const duration = motionMs("--dur-scramble")
  const start = performance.now()
  let frame = 0
  let handle = 0
  const finish = () => {
    cancelAnimationFrame(handle)
    for (const job of jobs) job.node.nodeValue = job.text
    stopRunning = null
  }
  const tick = (now: number) => {
    const progress = Math.min((now - start) / duration, 1)
    frame += 1
    if (frame % SHUFFLE_FRAMES === 0)
      for (const job of jobs) job.node.nodeValue = scrambled(job.text, progress)
    if (progress < 1) handle = requestAnimationFrame(tick)
    else finish()
  }
  stopRunning = finish
  for (const job of jobs) job.node.nodeValue = scrambled(job.text, 0)
  handle = requestAnimationFrame(tick)
}

function fadeProse(): void {
  const easing = readEasing("--ease-out")
  const duration = motionMs("--dur-panel")
  for (const paragraph of document.body.querySelectorAll("p")) {
    paragraph.animate({ opacity: [0, 1] }, { duration, easing })
  }
}

export async function withTextScramble(
  change: () => void,
  settle: () => Promise<void>,
): Promise<void> {
  stopRunning?.()
  flushSync(change)
  await settle()
  if (prefersReducedMotion() || typeof document.body.animate !== "function") return
  scramble(collect())
  fadeProse()
}
