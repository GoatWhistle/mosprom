# Open questions

Updated: 2026-10-23. Questions recorded, not sent.

| ID | Question | Decision affected | Source to consult | Status |
|---|---|---|---|---|
| Q1 | What are the weights, 3MF tolerances and G-code validity checks? | Priorities and validation thresholds | Case experts; PDF p. 11, website §6–8 | Open |
| Q2 | What are our checkpoint slots/timezone, defense duration, ZIP limits and other required fields? | Calendar and submission | Participant account; PDF pp. 7–10 | Open |
| Q3 | Which Windows machine will run the supplied STE Slicer and activated 5D modes? | Real integration and jury environment | Team; website §3–4, activation section | User chose a VM; installation and 5D activation pending |
| Q4 | What are the LLM quotas, image/tool support and permitted alternatives? | Agent integration and fallback | Organizers; website LLM section | Partly answered 2026-10-24: user confirmed timeweb `dashscope/qwen3.8-flash` is organizers' LLM; image_url and tool calling verified by one request each ([evidence](../docs/evidence.md)). Quotas and defect recognition on real photos open |
| Q5 | Is browser SPA opened by the plugin the intended interpretation of the PDF's embedded chat? | UI packaging | Website §3.2 versus PDF p. 2; confirm with experts if needed | User chose embedded chat with agent in plugin (ADR 0002); official source conflict remains |
| Q6 | What are the agreed P0, positioning, mechanisms, scope, metrics and owners? | Implementation plan | Next discussion with user | Agent moved into plugin (ADR 0002), unit-tested with fake slicer and scripted LLM; real Windows runtime pending |
| Q7 | How are physical DOCX constraints judged, and is post-processing allowed for the figurine? | Honest validation and scope | Experts; brief/MODELS.md | Open |

## Assumptions pending answers

- Year 2026 follows event context and website URL; PDF calendar omits year.
- Checkpoint timezone is not stated on p. 7; Moscow time is explicit only for submission/defense.
- Technical website supplements the PDF; publication dates do not establish which was newer.
- Hidden jury 3MF references cannot be used as a local measured baseline.
- Preliminary fleet-control scope is not supported by the received official brief.
