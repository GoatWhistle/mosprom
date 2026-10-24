# Project context

Project: Brim. Name and molten-plastic brand approved by user on 2026-10-23.
Event: Otkroy Mosprom, additive manufacturing case: FDM 3D/5D printing configuration.
Submission: October 25 before 10:00 MSK; defenses from 12:00 MSK (PDF p. 10).
Year 2026 inferred from event context; checkpoint timezone and personal slots need the participant account.
Brim 0.5.2 implements the agent in the plugin, embedded chat and browser SPA.
Verification and limits: [evidence](../docs/evidence.md); current documentation: [index](../docs/README.md).

## Current facts

| Topic | Status | Current fact | Evidence |
|---|---|---|---|
| Materials | Verified, 2026-10-23 | All 12 PDF pages and supplied transcript read; originals hashed | [Sources](../brief/sources/README.md) |
| Technical target | Verified from source, 2026-10-23 | STE Slicer plugin; Python 3.5/PyQt5; browser SPA on localhost; OpenAI-compatible API and MCP | [Technical task](../brief/TECHNICAL.md), §2–4 |
| Test data | Verified, 2026-10-23 | Seven DOCX/JPG/STL sets downloaded; DOCX read, images viewed, ZIP CRC and STL sizes checked | [Model tasks](../brief/MODELS.md), [manifest](../brief/sources/test-models-manifest.json) |
| Evaluation | Verified from source | Seven criteria, no weights; jury compares against private 3MF references | [Requirements](../brief/requirements.md) |
| Delivery | Verified from source | ZIP with plugin and per-model 3MF/G-code/chat screenshots | [Submission](../brief/PLATFORM.md) |
| Brand | Approved; implemented in existing files | Brim, molten-plastic accent; brand assets retained after frontend removal | [Visual system](../docs/visual-system.md) |
| Organizer LLM | Verified manually, 2026-10-24, n=1 each | timeweb `dashscope/qwen3.8-flash` confirmed by user as organizers'; accepts image_url and calls tools with an image; defect recognition on real photos untested | [Evidence](../docs/evidence.md) |
| Scope | Implemented on main; manual runs 2026-10-24 | Plugin agent, QML/SPA, local chat files; optional Claude proxy. Seven model exports recorded on 0.4.x; browser run on 0.5.2. No physical prints | [Evidence](../docs/evidence.md) |

## Pointers

- [Session](SESSION.md), [open questions](open-questions.md).
- [Brief](../brief/README.md), [event and resources](../brief/event.md).
- [Next discussion](../work/plan.md), [working artifacts](../work/README.md).
- [Product documentation](../docs/README.md), completed 2026-10-24; [analytics](../docs/analytics.md); [requirements map](../docs/requirements-map.md) covers R01–R17 with verification limits.
- Local verification 2026-10-24: plugin 153 passed / 2 skipped; backend 67 passed, Ruff/mypy passed. See evidence for methods.
