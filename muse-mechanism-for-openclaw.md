# Muse-style goal loop, built for OpenClaw — design

Den asked: can we implement what Muse has, for OpenClaw? Yes. Muse has no Judge, no goal tool, no post-turn hook — just a system-prompt instruction, a durable goal, and an hourly supervisor job. OpenClaw already has all the pieces. This is the design. Spec only — do not build until Den says so.

## What Muse has (recap)

1. A system-prompt instruction: create a goal when the user shares an enduring aspiration, a commitment, progress, or a setback — even without the word "goal".
2. The agent saves it as a DURABLE goal (Goals tab) — a milestone, not a per-session goal.
3. An hourly supervisor re-asserts that goal each run and picks the next highest-priority UNBLOCKED card.
4. A subagent builds the picked card.
5. The subagent updates the board.
6. Next hour, the supervisor runs again.

No per-session goal tool. No judge. No per-turn goal check.

## The OpenClaw mapping

| Muse piece | OpenClaw piece |
|---|---|
| System prompt | `AGENTS.md` — the agent's instructions file in its workspace |
| Durable goal (Goals tab) | `AGENTS.md` GOAL section — the goal text lives here, the supervisor reads it every run |
| Hourly supervisor (job) | OpenClaw cron job (automation), hourly, runs `agentTurn` on the supervisor agent |
| Board (cards) | Hermes kanban DB — `/home/engineer/.hermes/kanban.db` (Tony's board, `--board default`) |
| Subagent builds the card | Dispatched via `agentTurn` to `software-engineer` (or the owning agent) |
| Loop trigger | Hourly cron (not a per-turn hook) |

## The loop (same shape as Hermes and Muse)

Goal → work cycle → check → loop back.

1. **Supervisor job runs** (hourly, OpenClaw cron).
2. **Reads the GOAL** from `AGENTS.md`.
3. **Reads the board**, picks the next highest-priority UNBLOCKED card.
4. **Dispatches a subagent** via `agentTurn` (to `software-engineer`) with the card.
5. **Subagent builds the card**, updates the board (kanban).
6. **Supervisor job ends.**
7. **CHECK — is there a next unblocked card?** If yes, next hour the supervisor runs again (loop back). If no, the goal is done (or blocked) — the loop pauses until there is work.

## Files (dev-1)

- `AGENTS.md` — `/home/engineer/.openclaw/workspaces/<agent>/AGENTS.md` (goal instruction + GOAL section). Tony already has a GOAL section (goal + loop + escalation) — this design keeps it and adds the instruction.
- **Supervisor job** — OpenClaw cron, stored in `/home/engineer/.openclaw/state/openclaw.sqlite`, table `cron_jobs`. Hourly schedule, runs `agentTurn`. The job prompt tells the supervisor agent to read the GOAL, read the board, pick the next UNBLOCKED card, and dispatch a subagent.
- **Board** — `/home/engineer/.hermes/kanban.db` (Hermes kanban; Tony's board, `--board default`). Read with `hermes kanban stats` / `hermes kanban list --board default`. Never hand-edit the live DB.
- **Subagent** — dispatched via `agentTurn` to `software-engineer` (or the owning agent). Constraint: an `agentTurn` payload cannot use `sessionTarget main`; to target Tony's main session use `--session "session:agent:product-lead-agentpod:main"`.

## What this does NOT build

- No Judge. No per-turn goal check. The check is the supervisor looking for the next unblocked card each hour.
- No goal tool (`goal create/get/complete/wait`). No per-session goal registry. The goal is a section in `AGENTS.md`, not a tool call.
- No post-turn hook. The loop is driven by the hourly cron job, not by a hook after each turn.
- No heartbeat/idle-wake. The hourly schedule is the only trigger.

This is deliberately simpler than the Hermes mechanism (see `goal-mechanism-spec.md`). The Hermes spec has a Judge, a goal tool, a registry, and a post-turn hook — six known bugs to fix. This Muse-style design has none of that machinery. The trade-off: the loop is hourly (not per-turn), and there is no Judge to catch a stuck goal — the supervisor only sees the board.

## Implementation plan — 6 steps

1. **Add the goal instruction to `AGENTS.md`** (the system prompt). One paragraph: "When the user shares an enduring aspiration, a commitment with a timeframe, progress, or a setback, declare it as the goal in the GOAL section of this file — even without the word 'goal'."
2. **Agent writes the goal into the GOAL section of `AGENTS.md`** (durable). This is the "automatic" creation. The supervisor reads it every run.
3. **Create the hourly supervisor OpenClaw job** (cron, `agentTurn`). Schedule: hourly. The job prompt: read the GOAL from `AGENTS.md`, read the board, pick the next highest-priority UNBLOCKED card, dispatch a subagent via `agentTurn` with the card context.
4. **Supervisor reads GOAL + board, picks next UNBLOCKED card, dispatches subagent.** The supervisor does not build cards itself — it picks and dispatches.
5. **Subagent builds the card, updates the board (kanban).** One subagent per card. The subagent updates the card status and leaves a comment with proof.
6. **Verify: supervisor runs hourly, picks cards, board moves.** Check by readback: the job runs on schedule, a card moves from ready to running to done, the board counts change. No Judge, no goal tool.

## Open questions (for build time)

- Which agent is the supervisor? Tony (product-lead-agentpod) is the natural owner for AgentPod; Monica (product-lead-vibebrowser) for VibeBrowser. One supervisor job per product, or one job that covers both boards?
- How does the supervisor pick "highest-priority"? By kanban priority field, by card age, or by the goal's acceptance criteria? The Hermes board has a priority field — confirm it is set on cards.
- What happens when the board has no UNBLOCKED card? The job ends quietly (loop pauses) — or posts a "no work" note? Muse's supervisor just runs again next hour. Keep it quiet unless the goal is blocked.
- The old supervisor jobs (`tony-hourly-review`, `agentic-team-daily`, `goal-plugin-critic`) were removed 2026-11-15 on Den's order. This design is a NEW job with a different purpose (dispatch work, not review). Confirm Den wants it before creating it.

Diagram: drawn by `diagrams/gen-goal-mechanism-diagrams.py` (`openclaw-muse-design.svg`, PNG on the Notion page).
