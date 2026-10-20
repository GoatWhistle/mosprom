---
name: deck-motion
description: "Use when animating slides with the presentation engine: entry choreography, charts from data-viz, replay and seeded scenes."
---

# Deck motion

Motion on a slide is a diagram that moves: it shows the mechanism in the order the speaker
explains it. Snippets for every technique are in [recipes.md](recipes.md).

## Principles

- Everything is animated: every slide has an entry choreography, every element arrives in the
  order the speaker talks about it, the logo too. A slide where content just appears is unfinished.
- Each movement shows a step of the mechanism: data flows along the trace, a value settles, a bar
  grows to the measured value. If removing a motion loses no meaning, remove it.
- No hidden steps. A key press always moves to the next slide; nothing on a slide waits for a
  press. Everything the speaker talks about arrives in the entry choreography, in speaking order,
  and the slide is complete within 2.5 s (the cover within 3.5 s). If a part needs its own press,
  it is its own slide. The build fails on `data-steps`, `data-s`, `data-at` and `data-until`.
- Easing and durations come from the product tokens (`--ease-out`, `--ease-in-out`, `--dur-*`).
  No bounce, no elastic. Quiet loops (runners, an idle accent) only on the main path of the slide,
  marked `only-motion`.
- Deterministic: generative scenes use `deckKit.rng(seed)`, never `Math.random`, so the rehearsal,
  the defense and the PDF show the same picture.
- The final frame is the PDF page and the reduced-motion frame: it must contain everything.

## Engine contract

| Need | How |
| --- | --- |
| Enter choreography | Classes `.a` rise, `.f` fade, `.s` scale in, `.pop`, `.w` wipe, `.dr` line draw. `--d` delay and `--t` duration in seconds, inherited, so set them on a group. Runs when the slide gets `.play` |
| Slide-level animation | The engine puts `.play` on the slide element itself, so a slide rule is `#id.play .part`, never `.play #id .part` |
| Charts | `<div data-viz="columns" data-values="..." data-labels="a;b">`: the chart is drawn from data and animated with the same classes. Types and attributes: `presentation/library/README.md`, section Chart engine |
| Address | Hash `#5` opens slide 5 |
| Replay | `R` re-adds `.play`, restarts counters and QR, calls `scene.enter` again |
| Line drawing | `<path pathLength="1" class="dr">`; works for any SVG shape |
| Runner along a path | `.runner` inside a box the size of the SVG viewBox, `deckKit.followPath(runner, path)` in `init` |
| Count-up | `data-num="key"` plus class `count`; counts to the value from `numbers.json` |
| Scene logic | `scene.js`: `deckScene(id, { init(el), enter(el), leave(el), key(el, event) })` |
| Tween | `deckKit.tween({ from, to, dur, delay, curve: "out" \| "inOut" \| "linear", update, done })` returns a cancel function |
| Letters | `deckKit.letters(el)` splits text into spans with `--i` for staggered reveals |
| Reduced motion | `deckKit.reduced` and class `html.is-reduced`: one flag for prefers-reduced-motion, `?static` and `?print`. CSS animations jump to the end, tweens and the QR draw the final frame, `only-motion` elements hide |

## Animate a slide

1. Write the sequence as sentences first: what appears, in which order, and which spoken words
   each part lands on. The order of `--d` delays follows the order of the speech.
2. Build the static final frame; check it with `?static`.
3. Add choreography classes and `--d` per group. A part that cannot arrive on entry becomes the
   next slide, never a step.
4. Add `scene.js` only for what CSS cannot do: values from data, generative layouts, tweens.
5. Check frames: `npm run shots -- --slide <n> --at 0.3,0.8,1.5,3`, then press `R` live.

Done when: the slide is complete within 2.5 s, a key press changes the slide, `?static` and the
PDF page show the full content, and there are no console errors.

## Cover, final and QR

The logo assembly on the cover, the final lockup with «Готовы к вашим вопросам» and the QR
assembly have their own procedure: skill `deck-cover-final`. The rules above apply to them too.

## When to render video instead

Use the `hyperframes` plugin when the output is a file, not a live deck: the submission video,
a teaser, a social clip, an animated title for video, anything synced to voice-over or music, or a
continuous sequence longer than about 20 s. The deck stays in this engine because the speaker
controls the pace and the deck runs offline from one file. Embedding a rendered clip into a slide
is a last resort: it inflates `dist/deck.html` and cannot follow the speaker.
