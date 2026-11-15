# Goal

Research on how a session goal works: Hermes, Muse, and the OpenClaw spec.

One-line answer, both systems: the goal is auto-inferred. The agent itself reads the ask and declares the goal. Den never issues a set-goal command.

- **Hermes:** the agent calls a `goal` tool. The goal lives in one database row per session. A judge audits completion. The heartbeat feeds the goal back. See [hermes-goal-mechanism.md](hermes-goal-mechanism.md).
- **Muse:** Muse infers the goal from the project and declares it. An hourly supervisor re-asserts it each run and picks the next card. See [muse-goal-mechanism.md](muse-goal-mechanism.md).
- **OpenClaw:** spec only. Nothing is built. See [goal-mechanism-spec.md](goal-mechanism-spec.md).

Diagrams live in `diagrams/` as Mermaid source plus the generator that renders the PNGs. No PNGs in this repo. Rendered images are on the Notion page ([OpenClaw/Hermes goal plugin](https://app.notion.com/p/418ac25eb49f80f4a0a5e571a065c793)).

## Files

- `hermes-goal-mechanism.md` — how Hermes does it, from the code.
- `muse-goal-mechanism.md` — how Muse does it, from the design description and Muse's goal docs.
- `goal-mechanism-spec.md` — the OpenClaw build spec. Spec only.
- `diagrams/hermes-goal-mechanism.mmd`, `diagrams/muse-goal-mechanism.mmd` — diagram sources.
- `diagrams/gen-goal-mechanism-diagrams.py` — renders the PNGs from the same structure.

Status: spec only (2026-11-15). Do not start implementation until Den says so.
