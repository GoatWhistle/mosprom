import { clsx } from "clsx"
import styles from "./brand-mark.module.css"
import {
  MARK_PART,
  MARK_RINGS,
  MARK_VIEW_BOX,
  WORDMARK_BOWL,
  WORDMARK_DOT,
  WORDMARK_STROKE_WIDTH,
  WORDMARK_STROKES,
  WORDMARK_VIEW_BOX,
} from "./brand-paths"

export type BrandMotion = "none" | "intro" | "loop"

export interface BrandMarkProps {
  readonly motion?: BrandMotion
  readonly className?: string | undefined
}

const RING_CLASSES = [styles.ring1, styles.ring2, styles.ring3] as const
const MOTION_CLASSES: Readonly<Record<BrandMotion, string | undefined>> = {
  none: undefined,
  intro: styles.intro,
  loop: styles.loop,
}

export function BrandMark({ motion = "none", className }: BrandMarkProps) {
  return (
    <svg
      viewBox={MARK_VIEW_BOX}
      className={clsx(styles.mark, MOTION_CLASSES[motion], className)}
      aria-hidden="true"
      focusable="false"
    >
      <path className={clsx(styles.base, styles.part)} d={MARK_PART} />
      {MARK_RINGS.map((ring, index) => (
        <path
          key={ring}
          className={clsx(
            index === MARK_RINGS.length - 1 ? styles.accent : styles.base,
            styles.ring,
            RING_CLASSES[index],
          )}
          fillRule="evenodd"
          d={ring}
        />
      ))}
    </svg>
  )
}

export interface BrandWordmarkProps {
  readonly className?: string | undefined
}

export function BrandWordmark({ className }: BrandWordmarkProps) {
  return (
    <svg
      viewBox={WORDMARK_VIEW_BOX}
      className={clsx(styles.word, className)}
      aria-hidden="true"
      focusable="false"
    >
      <g className={styles.wordStroke} strokeWidth={WORDMARK_STROKE_WIDTH}>
        <path d={WORDMARK_STROKES} />
        <path d={WORDMARK_BOWL} />
      </g>
      <path className={styles.wordDot} d={WORDMARK_DOT} />
    </svg>
  )
}

export interface BrandLockupProps {
  readonly motion?: BrandMotion
  readonly className?: string | undefined
}

export function BrandLockup({ motion = "none", className }: BrandLockupProps) {
  return (
    <span className={clsx(styles.lockup, className)}>
      <BrandMark motion={motion} className={styles.lockupMark} />
      <BrandWordmark className={styles.lockupWord} />
    </span>
  )
}
