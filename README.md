# Goal

Research on how a session goal works: Hermes, Muse, and the OpenClaw spec.

One-line answer, both systems: the goal is auto-inferred. The agent itself reads the ask and declares the goal. Den never issues a set-goal command.

- **Hermes:** the agent calls a `goal` tool. The goal lives in one database row per session. A judge audits completion. The heartbeat feeds the goal back. See [hermes-goal-mechanism.md](hermes-goal-mechanism.md).
- **Muse:** Muse infers the goal from the project and declares it. An hourly supervisor re-asserts it each run and picks the next card. See [muse-goal-mechanism.md](muse-goal-mechanism.md).
- **OpenClaw:** spec only. Nothing is built. See [goal-mechanism-spec.md](goal-mechanism-spec.md).

Diagrams live in `diagrams/` as a Python generator that draws the PNGs. No PNGs in this repo.

## Files

- `hermes-goal-mechanism.md` — how Hermes does it, from the code.
- `muse-goal-mechanism.md` — how Muse does it, from the design description and Muse's goal docs.
- `goal-mechanism-spec.md` — the OpenClaw build spec. Spec only.
- `diagrams/gen-goal-mechanism-diagrams.py` — draws both diagrams (SVG, rendered to PNG at 3x). Mermaid was removed: GitHub's auto-layout can't match the sketch style.

Status: spec only (2026-11-15). Do not start implementation until Den says so.
