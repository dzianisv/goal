# Goal

Research on how a session goal works: Hermes, Muse, and the OpenClaw spec.

One-line answer, both systems: the goal is auto-inferred. The agent itself reads the ask and declares the goal. Den never issues a set-goal command.

- **Hermes:** the agent calls a `goal` tool. The goal lives in one database row per session. A judge audits completion. The heartbeat feeds the goal back. See [hermes-goal-mechanism.md](hermes-goal-mechanism.md).
- **Muse:** Muse infers the goal from the project and declares it. An hourly supervisor re-asserts it each run and picks the next card. See [muse-goal-mechanism.md](muse-goal-mechanism.md).
- **OpenClaw:** spec only. Nothing is built. See [goal-mechanism-spec.md](goal-mechanism-spec.md).

Diagrams are draw.io source in `diagrams/` (`.drawio` files). A CI job
(`.github/workflows/drawio-export.yml`) re-renders the PNG and SVG on
every `.drawio` change and commits them back, so the images in the repo
always match the source. The rendered `.drawio.png` / `.drawio.svg` files
live in the repo, so GitHub shows them as images, and each one still
contains the diagram XML — open it in draw.io to edit it.

The Python generator (`diagrams/gen-goal-mechanism-diagrams.py`) is kept
for now. It draws the same diagrams as SVG; the `.drawio` files are the
source of truth going forward.

## Files

- `hermes-goal-mechanism.md` — how Hermes does it, from the code.
- `muse-goal-mechanism.md` — how Muse does it, from the design description and Muse's goal docs.
- `goal-mechanism-spec.md` — the OpenClaw build spec. Spec only.
- `diagrams/hermes-goal-mechanism.drawio`, `diagrams/muse-goal-mechanism.drawio` — diagram sources (draw.io).
- `diagrams/hermes-goal-mechanism.drawio.png`, `diagrams/hermes-goal-mechanism.drawio.svg`, `diagrams/muse-goal-mechanism.drawio.png`, `diagrams/muse-goal-mechanism.drawio.svg` — rendered by CI from the `.drawio` files. Never edit by hand.
- `diagrams/gen-goal-mechanism-diagrams.py` — the earlier Python generator, kept for now.
- `.github/workflows/drawio-export.yml` — renders the PNG/SVG on every `.drawio` change.

Status: spec only (2026-11-15). Do not start implementation until Den says so.
