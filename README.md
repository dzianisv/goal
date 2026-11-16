# Goal

Research on how a session goal works: Hermes, Muse, and the OpenClaw spec.

One-line answer, both systems: the goal is auto-inferred. The agent itself reads the ask and declares the goal. Den never issues a set-goal command.

- **Hermes:** the agent calls a `goal` tool. The goal lives in one database row per session. A judge audits completion. The heartbeat feeds the goal back. See [hermes-goal-mechanism.md](hermes-goal-mechanism.md).
- **Muse:** research 2026-11-15 found no public evidence for an hourly supervisor that picks the next unblocked card, and no "Judge" in Meta Muse material — personal Muse is closed source. What is confirmed: durable goals in the Goals tab, worked on a schedule. The session-goal tool shape comes from Muse Code, the Judge shape from Hermes. See [muse-goal-mechanism.md](muse-goal-mechanism.md).
- **OpenClaw:** implementation underway on Den's 2026-11-16 order — reactive wake (kanban-wake plugin + goal plugin). Spec: [goal-mechanism-spec.md](goal-mechanism-spec.md).

Diagrams live in `diagrams/` as a Python generator that draws the PNGs. No PNGs in this repo. Rendered images go to the Notion page.

## Files

- `hermes-goal-mechanism.md` — how Hermes does it, from the code.
- `muse-goal-mechanism.md` — how Muse does it, from the design description and Muse's goal docs.
- `goal-mechanism-spec.md` — the OpenClaw build spec. Spec only.
- `diagrams/gen-goal-mechanism-diagrams.py` — draws both diagrams (SVG, rendered to PNG at 3x). The only diagram source. Mermaid and draw.io were both tried and removed: GitHub's Mermaid auto-layout can't match the sketch style, and draw.io is more work than the script.

Status: implementation underway (2026-11-16). Was spec-only until Den ordered the build.
