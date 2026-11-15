# Implementation spec — Hermes-like goal mechanism for OpenClaw

Status: SPEC ONLY. Den ordered 2026-11-15: write the spec, DO NOT start implementation.
Author: Ember. Date: 2026-11-15.
Reference: the Hermes goal implementation in `/home/engineer/.hermes/hermes-agent/` (read live 2026-11-15). All file/line citations below are from that repo.

## 1. What this is

A goal mechanism for OpenClaw agents, ported from Hermes, that lets an agent own a session goal the way Muse does: the agent declares the goal and its acceptance criteria itself, the goal is stored per session, a judge audits completion, and the heartbeat keeps the goal moving until it is done. For every agent, each with its own goal.

This is NOT a plugin, NOT a cron job that runs an inference turn, NOT goal text in a file, and NOT a guard script that reads the board. Those were all tried and removed (2026-11-15). The mechanism is a tool + a per-session registry + a judge.

## 2. The Hermes reference implementation (the truth)

Read these files in `/home/engineer/.hermes/hermes-agent/` before building anything. Do not design from prose.

### 2.1 The `goal` tool — `tools/goal_tool.py` (265 lines)

The agent calls it. Schema `GOAL_SCHEMA`. Actions: `get`, `create`, `link`, `complete`, `wait`.

- `get` — returns the current goal for the session, or `{"goal": None}`.
- `create` — `objective` (12–600 chars, one verifiable sentence) + `acceptance_criteria` (the observable end state the audit checks, written by the agent itself) + `verification` (how the audit confirms it: commands, URLs, checks) + optional `task_ids` (kanban card ids this goal is about) + optional `max_turns`. The agent declares the goal and its acceptance criteria — that declaration IS the "inference": the agent infers the goal from the user's ask and states it. Never create a goal for a plain question, a one-shot answer, or work the user cancelled.
- `link` — attach kanban card ids to the goal. Board wakes for cards NOT linked to the active goal are held until the next admitted wake.
- `complete` — `evidence` (what proves the acceptance criteria are met: commands run, URLs, ids). Runs the completion audit (`judge_goal`); refuses when the verdict is not DONE, so the agent cannot wave its own goal through.
- `wait` — parks the goal on a barrier: `on` = subagents | process | seconds | user, plus `reason`. Lifts when the barrier clears (a delegation returns, a process exits, the timer elapses, the user replies). `wait` on user is lifted only by a real user message.
- Rules the handler enforces (never the prompt alone):
  - `create` never overwrites a user-set goal. A user-set `/goal` always wins. It replaces the agent's OWN goal only with `replace=true` (the user redirected the work), archiving the old row.
  - `complete` runs the audit and refuses when the verdict is not DONE.
  - The goal is tagged `source="agent"` ("self-set" in the status line). Agent goals are never judged per turn, only heartbeat-continued (no turn budget).

Service-gated: the tool appears only when `goals.agent_tool` is on (see 2.4).

### 2.2 The registry — `hermes_cli/goals.py` (2513 lines)

- `GoalState` (line 603) — serializable per-session state: `goal` (text), `status` (active | waiting | done | cancelled), `revision`, `turns_used`, `max_turns`, `created_at`, `last_turn_at`, `last_verdict`, `last_reason`, `subgoals` (user-added criteria), `contract` (GoalContract: the five contract fields), `gates` (all must pass before the judge may declare done), `source` ("user" or "agent"), `linked_task_ids`, `pending_human_decisions`, `waiting_on_*` (barrier fields), `consecutive_stalled`, `consecutive_silent`, `consecutive_parse_failures`, `consecutive_transport_failures`, `resumed_after_wait`.
- Storage: one `state_meta` row `goal:<session_id>` in the SessionDB, JSON-serialized. `load_goal` (line 921), `save_goal` (line 942). Byte-stable per conversation.
- `GoalManager` (line 1521) — per-session goal state + continuation decisions. `evaluate_after_turn` calls the judge and returns the decision dict that drives the next turn. `next_continuation_prompt` (line 2300) is the canonical user-role message fed back into `run_conversation`. For agent goals it uses `_muse_kick_prompt` (a fixed sentence + contract/requirements + any questions already owed); for user goals `_continuation_body`.
- `judge_goal` (line 1313) — "Ask the auxiliary model whether the goal is satisfied." Returns `(verdict, reason, parse_failed, wait_directive, transport_failed)`; verdict is done / blocked / continue / wait / skipped. `parse_failed` means unusable output; transport errors set `transport_failed` and fail-open to `continue`.
- `evaluate_after_turn` (line ~2180):
  - Agent goals (`source == "agent"`): never judged per turn. Returns `("active", True, next_continuation_prompt(), "continue", "heartbeat")`. Completion goes only through `goal(action="complete", evidence=...)` + audit. No turn budget.
  - User goals: judged per turn by `judge_goal`. Verdicts drive continue / wait / blocked / done.
- `status_line` (line 1550) — human-readable goal status for `/goal status` and the tool view.

### 2.3 The prompt — `agent/prompt_builder.py` line 240, `GOAL_TOOL_GUIDANCE`

The system prompt does NOT contain the goal text. It contains only the instruction:

> "You own this session's goal. At the start of a turn that commits you to a multi-step outcome, call `goal(action=\"get\")`; if none is set, declare the outcome with `goal(action=\"create\", objective=..., acceptance_criteria=...)` before working — you state the acceptance criteria, the audit checks them. Keep working toward it until `goal(action=\"complete\")` passes with evidence; a refused completion means keep going, not re-phrase. Plain answers and cancelled work get no goal."

And the comment above it: "Muse-style goal ownership: the model declares the session goal itself (goals.agent_tool). Byte-stable per conversation; the live goal text comes back from `goal(action=\"get\"), never from the system prompt."

### 2.4 The gating — `agent/system_prompt.py` line 296, `toolsets.py` lines 26/133, `hermes_cli/goals.py` line 410

- The guidance is injected into the system prompt only when the `goal` tool is in the agent's toolset: `GOAL_TOOL_GUIDANCE if "goal" in names else None`.
- The tool is service-gated: it appears only when `goals.agent_tool` is on. `agent_goal_tool_enabled()` (line 410): `load_config().get("goals") or {}).get("agent_tool") is True` — strict `is True`, so a stray string like `"false"` cannot switch it on; fails closed. Off by default.
- `toolsets.py` line 26: `"goal",  # service-gated: appears only when goals.agent_tool is on`. Line 133: `"goal": _ts("Session goal the agent declares and closes itself (goals.agent_tool)", ["goal"])`.

### 2.5 The user side — `/goal` command

`hermes_cli/goal_command.py` + `hermes_cli/cli_commands_mixin.py` line 2297 (`_handle_goal_command`). The user sets the goal with `/goal <text>`. A user-set goal always wins and cannot be replaced by the agent's tool. `/goal status` shows the status line. `/goal wait`, `/goal resume`, `/goal clear`, `/goal gate add <cmd>` (gates: ALL must pass before the judge may declare done). `/subgoal` adds user criteria.

### 2.6 What the heartbeat does

The heartbeat continues an active goal: it feeds `next_continuation_prompt()` back into the conversation as a user-role message. For agent goals the kick is a fixed sentence + contract/requirements. The goal is never judged per turn for agent goals; the heartbeat is the continuation mechanism. The heartbeat prompt files (`heartbeat-focus-prompt.md`, `heartbeat-prompt.md` in a profile) are ONE agent's tick routine containing goal text for that agent's workflow — they are NOT the goal mechanism. Do not confuse them again.

## 3. Known bugs in the Hermes implementation (DO NOT copy these)

Verified from the code. The OpenClaw version must fix each one, not reproduce it.

1. **Goal dies at context compression.** `load_goal` does a flat `goal:<session_id>` lookup with no parent-lineage walk. Context compression rotates `session_id` to a fresh child session, so an active goal silently dies at compression. `migrate_goal_to_session` exists to carry a goal to a continuation, but it is best-effort only ("Best-effort, never raises (a failure here must not block compression)"). Fix: the registry must resolve a goal through the session's parent lineage, or the goal must be keyed to a stable agent/conversation id that survives compression, not to a rotating session id.
2. **Agent goals have no per-turn judge and no turn budget.** Line 2182: "Agent goals are never judged per turn (heartbeat continuation only, no turn budget)." An agent-set goal can run indefinitely without any progress check. `consecutive_stalled` (line 659, incremented at line 2288 when a judged reply repeats the previous one) exists, but it only increments inside `evaluate_after_turn` AFTER the judge runs — and agent goals return early before the judge, so `consecutive_stalled` never increments for them. Fix: agent goals need a stall detector that works without a per-turn judge (e.g. count heartbeat continuations with no observable progress, and pause after N), and a turn/heartbeat budget.
3. **Judge unreachable = never pause (silent failure).** `_judge_outage` (line 2258): "Judge API unreachable. The goal's state never depends on judge availability: keep it active, hold a short backoff timer, alert the operator once, resume on the next good verdict. The turn is not charged to the goal (the judge, not the agent, failed)." And `judge_goal` fails open to `continue` on transport errors. If the judge is down, the goal keeps running with no audit, indefinitely, and the only signal is a single operator alert. Fix: after N consecutive judge outages, pause the goal and surface it as a blocker (not a single alert that can be missed); do not keep an unaudited goal active forever.
4. **Self-graded acceptance criteria.** The agent writes its own acceptance criteria, and the audit checks those criteria. Weak criteria pass easily. There is no independent check that the criteria actually capture the user's ask. Fix: when the goal comes from a user-set goal, derive the acceptance criteria from the user's text (or require the user to state them); when the agent declares the goal, have the judge verify the criteria against the original user ask (not just against the evidence). At minimum, record the user ask alongside the agent-written criteria so the audit can compare them.
5. **Stop-check plugin broken on Linux.** The `agentpod-stop-check` plugin in `plugins/` is a symlink pointing to a macOS path (`/Users/engineer/.hermes/plugins/agentpod-stop-check`), so it does not load on the Linux VM. The stop-check (the agent cannot end a turn while a card it owns is unattended or a promise has no card/cron behind it) is therefore not enforced here. Fix: the stop-check must be a real, loadable mechanism on the deployment target, not a symlink to another OS's path. In OpenClaw this is a gap (see 4.3).
6. **Goal tool off by default.** `goals.agent_tool` fails closed and is off by default. The mechanism is inactive unless explicitly enabled per profile. This is a config gap, not a code bug, but it means the mechanism silently does nothing unless someone opts in. Fix: the OpenClaw version should be ON by default for agents that have a goal, with an explicit opt-out, so the mechanism is not silently absent.

## 4. OpenClaw adaptation (what to build)

Map each Hermes piece to OpenClaw. "Missing" means OpenClaw has no equivalent and it must be built; "exists" means use it.

### 4.1 The `goal` tool — BUILD

OpenClaw agents have tools, but there is no `goal` tool. Build one with the same interface as Hermes `GOAL_SCHEMA` (`tools/goal_tool.py`): actions `get`, `create`, `link`, `complete`, `wait`, with the same parameters (`objective`, `acceptance_criteria`, `verification`, `evidence`, `task_ids`, `max_turns`, `replace`, `on`, `process_session`, `seconds`, `question`, `reason`). Enforce the same handler rules (never the prompt alone):
- `create` never overwrites a user-set goal.
- `complete` runs the audit and refuses when the verdict is not DONE.
- `wait` parks the goal on a barrier.

Implementation route (to be decided at build time, not in this spec): OpenClaw's tool/extension mechanism. If OpenClaw has no way to add a custom tool, the closest working mechanism is a skill that exposes the same operations via the agent's existing tools (e.g. a CLI/script the agent calls). Do NOT implement it as a cron job that runs an inference turn — that was the removed mistake.

### 4.2 The registry — BUILD

OpenClaw has a state store (SQLite, `~/.openclaw/state/`). Store one goal row per agent session, keyed to a stable id that survives compaction/rotation (fix Hermes bug 1). Fields: the same as Hermes `GoalState` (goal, status, source, contract, gates, subgoals, linked_task_ids, turns_used, max_turns, waiting_*, consecutive_stalled, etc.). The registry must be readable by the goal tool (`get`), by the judge, and by the heartbeat continuation. Do NOT store the goal in a file (no GOAL_STATE.md, no goal text in AGENTS.md).

### 4.3 The judge — BUILD (hardest part)

Hermes `judge_goal` is an auxiliary-model call after each turn. OpenClaw has NO post-turn hook — there is no way to run code automatically after an agent turn. This is the biggest gap. Options (choose at build time; the spec does not pick one):
- (a) The agent itself calls the judge (via a tool) at the end of a turn that commits to the goal. Weakest — relies on the agent remembering.
- (b) A scheduled job runs the judge on a cadence (e.g. hourly) and posts the verdict back to the agent's session. This is a job, but it is NOT an inference job that nudges the agent — it is the audit, and it only runs the judge, not a full agent turn. Still, it spends inference on a schedule.
- (c) The heartbeat runs the judge: on each heartbeat tick, before continuing the goal, run the judge on the last turn and decide continue/wait/done/blocked. This keeps the judge inside the agent's own turns (no separate job). This is the closest to Hermes (where the judge runs in `evaluate_after_turn`).
- Whichever is chosen, the judge must be a SEPARATE, cheap model call (not the agent's main turn), and its verdict must be recorded in the registry (last_verdict, last_reason). Fix Hermes bug 3: after N consecutive judge outages, pause the goal and surface it as a blocker.

The stop-check (Hermes bug 5) is part of the judge path: the agent cannot end a turn while a card it owns is unattended or a promise has no card/cron behind it. In OpenClaw there is no turn-end hook. The closest mechanism is the system-prompt guidance (the agent checks itself before ending a turn) plus the judge flagging an unattended card as a BLOCKED verdict. Record this as a known limitation, not as a solved problem.

### 4.4 The heartbeat continuation — EXISTS (with a gap)

OpenClaw has a heartbeat (system-owned, every 30 min) that wakes the agent's main session. The continuation is: on each heartbeat, the agent calls `goal(action="get")`, and if a goal is active, it continues it (the heartbeat feeds the goal back into the turn). The gap: the heartbeat is bare (no prompt) and system-owned (cannot be edited to carry a prompt). The goal re-assertion therefore depends on the agent's instructions (the GOAL_TOOL_GUIDANCE in AGENTS.md, see 4.5) telling it to call `get` at the start of every turn, including heartbeats. Do NOT add a separate inference job to nudge the agent — the heartbeat + the guidance is the mechanism.

### 4.5 The prompt guidance — EXISTS (use correctly)

OpenClaw agents have AGENTS.md (the system prompt). Put ONLY the `GOAL_TOOL_GUIDANCE` text there (the instruction to use the tool), adapted to OpenClaw's tool name. Do NOT put the goal text, the acceptance criteria, or a routine in AGENTS.md. The live goal text comes back from `goal(action="get")`, never from the system prompt. This is the correct use of AGENTS.md for the goal mechanism; the earlier mistake was putting the goal itself in the file.

### 4.6 The gating — BUILD

Mirror Hermes: the `goal` tool appears only when the agent opts in (a per-agent config flag, e.g. `goals.agent_tool: true`). Unlike Hermes bug 6, default it ON for agents that have a goal set by Den, with an explicit opt-out. The guidance is injected into the system prompt only when the tool is in the agent's toolset.

### 4.7 The user side — BUILD

Den sets the goal. Mirror Hermes `/goal`: a way for Den to set the goal for an agent (a command, a config entry, or a message to the agent). A user-set goal always wins and cannot be replaced by the agent's tool. `/goal status` shows the status line. The goal is a quantified outcome (e.g. "public release ready, first $10K MRR"), not a task list. This is the override. The normal flow is auto-inference: the agent declares the goal itself from the ask.

## 5. Acceptance criteria (how to know it is done)

Do not call it done until ALL of these are verified by live readback, not by reading a design doc.

1. The `goal` tool exists and is callable by an agent. `goal(action="get")` returns None when no goal is set; `goal(action="create", objective=..., acceptance_criteria=...)` creates one and `get` returns it; `goal(action="complete", evidence=...)` refuses when the evidence does not satisfy the criteria (audit) and completes when it does.
2. A user-set goal cannot be overwritten by the agent's `create` (returns an error naming the user-set goal).
3. The goal survives a session compaction/rotation (fix for bug 1) — verified by setting a goal, compacting/rotating the session, and calling `get` on the new session id.
4. An agent-set goal that makes no progress is paused by the stall detector (fix for bug 2) — verified by N heartbeat continuations with no observable progress.
5. A judge outage pauses the goal after N consecutive failures and surfaces it as a blocker (fix for bug 3) — verified by making the judge unreachable and observing the pause.
6. The acceptance criteria are checked against the original user ask, not just the evidence (fix for bug 4) — verified by an agent writing weak criteria for a goal whose user ask demands more, and the audit refusing.
7. The goal text is NOT in any file (no GOAL_STATE.md, no goal text in AGENTS.md). The only goal text in AGENTS.md is the tool-use guidance. Verified by grep.
8. No inference job exists whose purpose is to nudge the agent about the goal. Verified by listing the agent's jobs.
9. The heartbeat continues an active goal: on a heartbeat tick with an active goal, the agent calls `get` and works the next step (verified by the heartbeat's tool calls, not by a status message).
10. Tony (product-lead-agentpod) and Monica (product-lead-vibebrowser) both have the mechanism, each with their own goal, and both pass 1–9.

## 6. Out of scope (do not build)

- A plugin (OpenClaw has no plugin system for this; and the mechanism is a tool + registry + judge, not a plugin).
- A cron job that runs an inference turn to nudge the agent (the removed tony-goal-nudge mistake).
- Goal text in a file (AGENTS.md, GOAL_STATE.md, or any other file).
- Guard scripts that read the board (focus_guard.py, blocked_reason_guard.py — removed 2026-11-15).
- A design diagram of the OLD guessed design (the goal-plugin-design diagram is wrong and superseded; do not rebuild it). The current diagrams live in `diagrams/` (Mermaid source + generator) and on the Notion page; they show the real mechanism, not the guess.

## 7. Open questions (for Den, only when the build starts)

- Which judge model (cheap auxiliary model, or the agent's own model)? Hermes uses an auxiliary model via `agent.auxiliary_client.call_llm`.
- Which option for the judge trigger (4.3a / 4.3b / 4.3c)? The spec does not pick one.
- How does Den set the goal (command, config, or message)? Hermes uses `/goal <text>`.
- What is the stall limit N (bug 2 fix) and the judge-outage limit N (bug 3 fix)? Hermes uses `max_stalled_turns()` and a backoff; pick numbers at build time.

## 8. History (why this spec exists)

- 2026-11-14: Ember built a file-based approximation (goal text in AGENTS.md + guard scripts + GOAL_STATE.md + a cron nudge job) and a diagram of it. Den rejected it: the diagram did not show the mechanism, and the design was guessed, not read from the Hermes code.
- 2026-11-15 01:07: Den ordered a 4h critic job to push the work like he would.
- 2026-11-15 01:24: Den: "That is complete fail. 49 blocked tasks when blockers are only payments and credentials." (Separate issue: the 49 blocked VibeBrowser cards. Still open.)
- 2026-11-15: Den: "That is invalid design to use inference job. Think more on the design. How is it implemented for Hermes." Ember read the Hermes code and found the goal tool + registry + judge (not prompt files).
- 2026-11-15: Den: "Then implement inside OpenClaw, not plugin." Ember implemented the file-based approximation inside OpenClaw (AGENTS.md + guard scripts). Den: "You did a complete bullshit. How Hermes goal inference is implemented in the repo in pointed?" Ember pointed to the real mechanism (goal tool + registry + judge).
- 2026-11-15: Den: "Remove the shit you implemented" + "Create an implementation spec for Hermes like goal but don't start implementation. Hermes one has bugs." This spec is the result. The file-based implementation is removed (verified: AGENTS.md reverted, guard scripts deleted, GOAL_STATE.md deleted, nudge job removed, hourly review + critic jobs updated).
- 2026-11-15: Diagrams rebuilt in Den's sketch style (OpenClaw → profiles → sessions → message flow → tools on the side). They show auto-inference and injection (heartbeat tick + 15-min idle re-poke for Hermes; hourly supervisor for Muse). Sources in `diagrams/`, rendered PNGs on the Notion page. No PNGs in this repo.
- 2026-11-15: Correction — Muse sets the goal automatically. An earlier draft said "Den sets the project goal once." That line exists nowhere in the source; it was invented. The truth (docs/goals.md + system prompt + spec lines 9/50): the model declares the session goal itself, with no set-goal command from Den. Same auto-inference as Hermes.
- 2026-11-15: Den stopped the OpenClaw audit/fix jobs (tony-hourly-review, agentic-team-daily, goal-plugin-critic). The CEO daily review still runs.
