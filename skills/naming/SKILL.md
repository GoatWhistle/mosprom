---
name: naming
description: "Use when generating, scoring or choosing a product name, tagline and name origin."
---

A hackathon name has one job: the jury remembers it after one hearing and it tells the story of the product's mechanism. A clever name that needs explanation loses to a plain one that explains itself.

## Inputs

Read `AGENTS.md` (thesis), `brief/requirements.md` (audience, jury language) and the three solutions. Write down in one line each: the core mechanism (a verb), the domain's own technical terms, the user, the feeling after using it. If the thesis is not fixed yet, stop and run `hack-kickoff` first.

## Generate wide

At least 30 candidates across these routes, at least 4 per route:

| Route | Idea | Shape |
| --- | --- | --- |
| Procedure | the domain term for what the product does | "the name is the procedure, not a metaphor" |
| Mechanism metaphor | a physical process with the same shape | a short concrete noun |
| Instrument | the tool a professional would use for this | calibration, gauge, lens words |
| Coined | a clipped or blended word from the mechanism | 4–7 letters, one stress |
| Verb | the action the user takes | imperative or gerund |
| Outcome | what is true after use | adjective or state noun |

Default form: one short latin word, lowercase, 4–8 letters, easy to say for both Russian and English speakers. Avoid filler suffixes and words (`-ify`, `-ly`, `AI`, `GPT`, `Smart`, `Hub`, `Pro`, `Bot`, `Assist`), dictionary words with a big existing brand, and anything that needs spelling out loud.

## Score the shortlist

Pick 8 and score each 1–5:

- **Story fit** — the name maps to the mechanism without a slide explaining it.
- **Say it once** — heard once, written correctly in RU and EN.
- **Mark potential** — a letterform or shape that survives at 16px.
- **Distinct** — no direct collision in the domain; quick web search, GitHub, npm, an obvious domain and trademark check (record "known uses" honestly).
- **Pitch sentence** — read "Meet ___, a ___ that ___." aloud; it must sound natural.

Also check meanings in Russian, English and slang; drop anything with an unlucky reading.

## Tagline

5–8 options, at most 8 words, concrete. Strongest shapes: a promise with a contrast ("Every match has a reason."), a negation ("…which cannot be gamed"), a split role ("The model suggests. The expert decides."). No superlatives, no "AI-powered", no "платформа".

## Output

Write `work/naming.md` (internal, scrubbed at submission): the full candidate list by route, the scored table for the 8, two finalists with the reasoning, 5–8 taglines, and for the recommended name:

- the **origin in one phrase** for README "Идея" ("Название — от …: …");
- a **typographic device** that encodes the mechanism (a letter replaced by a mark, a dot that moves) for `brand-identity`;
- the pitch sentence.

Done: the user has picked the name and tagline; `AGENTS.md` header, `README.md` header and `frontend/PRODUCT.md` use them.
