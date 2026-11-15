# How Hermes does it

Read from the code in `/home/engineer/.hermes/hermes-agent/`. Verified 2026-11-15.

The goal is a tool, a registry, and a judge. Not a file.

## The goal is auto-inferred

The main session decides. The agent itself, in the same turn as the user message, reads the ask, decides it is a multi-step outcome, and calls `goal(action="create")` with the objective and acceptance criteria it writes itself. That call is the inference.

No background API call infers the goal. The only other model call is the judge, and it only asks whether the goal is done.

## The tool — `tools/goal_tool.py` (265 lines)

The agent calls it. Actions: get, create, link, complete, wait.

- **get** — returns the current goal, or `{"goal": None}`.
- **create** — objective (12–600 chars) + acceptance criteria (the agent writes both) + verification + optional `task_ids` + optional `max_turns`. Never create a goal for a plain question, a one-shot answer, or cancelled work.
- **link** — attach kanban card ids to the goal.
- **complete** — evidence. Runs the completion audit (`judge_goal`). Refuses unless the verdict is DONE.
- **wait** — parks the goal on a barrier: subagents, process, seconds, or user.

Rules the handler enforces:

- `create` never overwrites a user-set goal. A user-set `/goal` always wins.
- `complete` runs the audit and refuses when the verdict is not DONE.
- The goal is tagged `source="agent"` ("self-set"). Agent goals are never judged per turn, only heartbeat-continued. No turn budget.

The tool appears only when `goals.agent_tool` is on. Off by default.

## The registry — `hermes_cli/goals.py` (2513 lines)

One `state_meta` row per session: `goal:<session_id>` in the SessionDB. JSON. `load_goal` (line 921), `save_goal` (line 942).

`GoalState` (line 603) holds: goal text, status (active / waiting / done / cancelled), revision, `turns_used`, `max_turns`, contract, gates, source (user / agent), `linked_task_ids`, `pending_human_decisions`, `waiting_on_*` barriers, `consecutive_stalled`, `consecutive_silent`, `consecutive_parse_failures`, `consecutive_transport_failures`, `resumed_after_wait`.

`GoalManager` (line 1521) decides what happens after each turn.

## The judge — `judge_goal` (line 1313)

"Ask the auxiliary model whether the goal is satisfied." Returns verdict (done / blocked / continue / wait / skipped), reason, `parse_failed`, `wait_directive`, `transport_failed`. Transport errors fail open to `continue`.

`evaluate_after_turn` (line ~2180):

- Agent goals: never judged per turn. Returns `("active", True, next_continuation_prompt(), "continue", "heartbeat")`. Completion goes only through `complete` + audit.
- User goals: judged per turn. Verdicts drive continue / wait / blocked / done.

## The loop (one turn, then the next)

1. **Turn starts.** A user message arrives (or a heartbeat tick feeds the goal back as a user-role message).
2. **AI message.** The agent reads the turn. If it commits to a multi-step outcome and no goal is set, it calls `goal(action="create")` — that is the inference, in the main session, in this same turn.
3. **Tool calls, then results.** The agent calls tools (`goal`, `read`, `write`). Results come back. AI message → tool calls → results repeats until the agent stops calling tools.
4. **Turn ends.**
5. **Judge runs** (background, auxiliary model). It asks only "is the goal DONE?" — but only for USER-set goals. Agent goals skip the per-turn judge; the heartbeat just continues them. The judge also runs when the agent calls `goal(complete, evidence)` — the audit.
6. **Next turn.** Verdict `continue` → the heartbeat tick feeds the goal back as a user-role message, and the loop starts again at step 1. Idle 15 min → the barrier-wake chore re-pokes the goal.

## The prompt — `agent/prompt_builder.py` line 240

The system prompt holds only the instruction to use the tool (`GOAL_TOOL_GUIDANCE`). The goal text never lives in the prompt. It comes back from `goal(action="get")`.

> "You own this session's goal. At the start of a turn that commits you to a multi-step outcome, call `goal(action="get")`; if none is set, declare the outcome with `goal(action="create", objective=..., acceptance_criteria=...)` before working — you state the acceptance criteria, the audit checks them. Keep working toward it until `goal(action="complete")` passes with evidence; a refused completion means keep going, not re-phrase."

Comment above it: "Muse-style goal ownership: the model declares the session goal itself (goals.agent_tool). Byte-stable per conversation; the live goal text comes back from `goal(action="get")`, never from the system prompt."

## The gate — `agent/system_prompt.py` line 296, `toolsets.py` lines 26/133, `hermes_cli/goals.py` line 410

The guidance is injected only when the `goal` tool is in the agent's toolset. The tool appears only when `goals.agent_tool` is on — strict `is True`, fails closed. Off by default.

## The user side — `/goal`

`hermes_cli/goal_command.py` + `cli_commands_mixin.py` line 2297. Den sets a goal with `/goal <text>`. A user-set goal always wins and cannot be replaced by the agent's tool. `/goal status` shows the status line. `/goal wait`, `/goal resume`, `/goal clear`, `/goal gate add <cmd>`, `/subgoal`.

This is an override, not the flow. The flow is auto-inference.

## What feeds the goal back (injection)

Two triggers. Both re-assert the existing goal. Neither infers a new one.

1. **Heartbeat tick.** `next_continuation_prompt` (line 2300) feeds the goal back as a user-role message into `run_conversation`. For agent goals it uses `_muse_kick_prompt` (a fixed sentence + contract/requirements).
2. **Idle-wake.** The barrier-wake chore re-pokes an active goal with no turn for `idle_wake_seconds` (default 900s = 15 min). `list_idle_active_goals` (line 1086).

## The pieces around it

In `~/.hermes/profiles/<profile>/plugins/<name>/`:

- **Focus coach** (hourly). Compares board and GitHub against the launch gates, names what the EM is not working on.
- **agentpod-stop-check.** The EM cannot end a turn while a card it owns is unattended or a promise has no card or cron behind it.
- **kanban-wake.** Receives the dispatcher's signed webhook, turns board events into EM turns. Unsigned requests get 401.
- **blocked_reason_guard.** Fails the tick if a blocked card has no BLOCKER: line or has been blocked over 24h.
- **brief-gate.** Parks engineer cards whose text lacks DESIGN:, SCOPE:, ACCEPTANCE:, PROOF:.

The heartbeat prompt files (`heartbeat-focus-prompt.md`, `heartbeat-prompt.md`) are one agent's tick routine. They are NOT the goal mechanism.

## Known bugs (do not copy)

1. **Goal dies at context compression.** `load_goal` does a flat `goal:<session_id>` lookup, no parent walk. Compression rotates the session id, so the goal silently dies. `migrate_goal_to_session` is best-effort only.
2. **Agent goals have no per-turn judge or turn budget.** No stall detection. `consecutive_stalled` only increments after the judge runs, and agent goals return before the judge.
3. **A dead judge never pauses the goal.** `judge_goal` fails open to `continue`. `_judge_outage` (line 2258): keep active, short backoff, alert once. No pause.
4. **Self-graded acceptance criteria.** The agent writes them, the audit checks them. Weak criteria pass.
5. **Stop-check plugin broken on Linux.** Symlink to a macOS path (`/Users/engineer/.hermes/plugins/agentpod-stop-check`). Does not load.
6. **Goal tool off by default.** Silent unless opted in.

Diagram: drawn by `diagrams/gen-goal-mechanism-diagrams.py` (PNG on the Notion page).
