# Project context

Project: Brim. Name and molten-plastic brand approved by user on 2026-10-23.
Event: Otkroy Mosprom, additive manufacturing case: FDM 3D/5D printing configuration.
Submission: October 25 before 10:00 MSK; defenses from 12:00 MSK (PDF p. 10).
Year 2026 inferred from event context; checkpoint timezone and personal slots need the participant account.
Agent and embedded plugin implemented; automated verification recorded in work/implementation-verification.md. Embedded chat selected; standalone frontend removed.

## Current facts

| Topic | Status | Current fact | Evidence |
|---|---|---|---|
| Materials | Verified, 2026-10-23 | All 12 PDF pages and supplied transcript read; originals hashed | [Sources](../brief/sources/README.md) |
| Technical target | Verified from source, 2026-10-23 | STE Slicer plugin; Python 3.5/PyQt5; browser SPA on localhost; OpenAI-compatible API and MCP | [Technical task](../brief/TECHNICAL.md), §2–4 |
| Test data | Verified, 2026-10-23 | Seven DOCX/JPG/STL sets downloaded; DOCX read, images viewed, ZIP CRC and STL sizes checked | [Model tasks](../brief/MODELS.md), [manifest](../brief/sources/test-models-manifest.json) |
| Evaluation | Verified from source | Seven criteria, no weights; jury compares against private 3MF references | [Requirements](../brief/requirements.md) |
| Delivery | Verified from source | ZIP with plugin and per-model 3MF/G-code/chat screenshots | [Submission](../brief/PLATFORM.md) |
| Brand | Approved; implemented in existing files | Brim, molten-plastic accent; brand assets retained after frontend removal | [Visual system](../docs/visual-system.md) |
| Organizer LLM | Verified manually, 2026-10-24, n=1 each | timeweb `dashscope/qwen3.8-flash` confirmed by user as organizers'; accepts image_url and calls tools with an image; defect recognition on real photos untested | [Analytics](../docs/analytics.md#llm-организаторов) |
| Scope | Approved by user; implemented on branch | Embedded STE Slicer chat; agent runs in plugin as OpenAI client + MCP host, no DB; backend only proxies Claude. STE Slicer runtime of 0.3.0 unverified | [ADR 0002](../docs/adr/0002-plugin-agent-openai-mcp-host.md) |

## Pointers

- [Session](SESSION.md), [open questions](open-questions.md).
- [Brief](../brief/README.md), [event and resources](../brief/event.md).
- [Next discussion](../work/plan.md), [working artifacts](../work/README.md).
- [Product documentation](../docs/README.md); several pages remain template drafts.
