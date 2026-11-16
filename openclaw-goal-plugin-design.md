# OpenClaw goal plugin — design

Status: design doc for the built plugin. Written 2026-11-16. Implementation
lives in `~/workspace/goal-plugin/` (`goal` plugin) and `~/workspace/goal-tool/`
(`goal-tool` plugin), installed on dev-1 at `/home/engineer/.openclaw/`.
Build report: `~/workspace/goal-plugin/BUILD-REPORT.md` — this doc does not
re-state verified items as anything else; where the build report says NOT
verified, this doc says the same.

Spec: [goal-mechanism-spec.md](goal-mechanism-spec.md) (Hermes goal tool +
registry + Judge, written 2026-11-15; was spec-only until Den ordered the
build 2026-11-16). This doc records what was actually built, where it
differs from the spec, and what is still open.

Note on the spec's §6: it says "NOT a plugin". That was written before Den
ordered the build. Den's standing rule for this work is **plugin FIRST, no
fork of OpenClaw core** — the plugin route below is what was ordered and built.

## (a) What is being mirrored from Muse

### The live Muse tool surface

Personal Muse exposes these goal tools (listed live 2026-11-15):

`user_goal.create / list / search / get / update / set_status
(active/completed) / create_entry / update_entry / delete_entry / delete`
(+ `delete_briefing`). Tracking is a separate surface.

The plugin's `goal` tool mirrors that surface. Actions already built:
`get / create / link / complete / wait / resume / clear`. Actions being
added by a parallel workstream to complete the mirror: `list / search /
update / set_status / create_entry / delete_entry / delete`.

### The correction — what is NOT being mirrored

The earlier design doc ([muse-goal-mechanism.md](muse-goal-mechanism.md),
now corrected) claimed personal Muse works by a system-prompt instruction
that auto-creates a durable goal from an enduring aspiration, plus an hourly
supervisor that re-reads the goal and picks the next highest-priority
unblocked card. Research on 2026-11-15 found **no public evidence** for
either claim, and the hourly-supervisor + Judge shape exists publicly only
in Hermes/AgentPod, which explicitly copied Muse Code — not personal Muse.
Personal Muse is closed source; its internals are unverified.

So the honest lineage of this plugin is:

- **Session-goal tool shape: Muse Code**, the sibling product, which
  documents `get_goal / create_goal / update_goal / report_progress`,
  session-scoped, with a post-turn follow-up queue that keeps the agent
  working toward a set goal and a requirement-by-requirement completion
  check before the goal may be declared done.
- **Judge + registry + push shape: Hermes**, read from its code
  (`tools/goal_tool.py`, `hermes_cli/goals.py`), which is where the
  per-turn Judge, the stall counters, and the continuation prompt come from.
- **Durable-goal surface: personal Muse's `user_goal.*` tools** (above) —
  the only part of personal Muse that is publicly visible and live.

Nothing in this plugin claims to reproduce personal Muse's internals.

## (b) Architecture

### Two plugins, one mechanism

| Plugin | Entry | Job |
|---|---|---|
| `goal` | `definePluginEntry` | Turn-end Judge + push. Registers the `agent_end` hook only. No tool. |
| `goal-tool` | `defineToolPlugin` | Exposes the `goal` tool to agents. Shares the registry + handler with `goal` (imports from `../goal-plugin/dist/`). |

**Why two.** `api.registerTool` inside a `definePluginEntry` does NOT expose
a tool to agents. The runtime only builds agents' tool lists from tools
declared via `defineToolPlugin` (the metadata is attached to the entry), and
the registry also requires the manifest to declare `contracts.tools`. The
first build registered the tool inside `definePluginEntry`; the factory was
never called and Tony got "Tool named `goal` is not available". The fix is
the separate `goal-tool` plugin. Its `openclaw.plugin.json` declares
`"contracts": {"tools": ["goal"]}` — required; the gateway rejects tool
registration without it.

### Registry

SQLite `goal.db` in the OpenClaw state dir — a separate file from the
gateway's own `openclaw.sqlite`, so the plugin never contends with the
gateway's writes. One row per session, keyed to the session KEY
(`agent:<id>:main`), NOT a rotating session id. The session key is stable
and survives compaction/rotation (Hermes bug 1 fix). The live goal state
lives ONLY here, never in a file.

Schema (`src/registry.ts`, table `goals`, `session_key` PRIMARY KEY):

| Field | Meaning |
|---|---|
| `session_key`, `agent_id` | Row identity: session key + owning agent |
| `goal` | Goal text (one verifiable sentence) |
| `acceptance_criteria` | Observable end state the audit checks (agent-written) |
| `verification` | How the audit confirms it (commands, URLs, checks) |
| `user_ask` | **The original user ask**, stored so the judge can check the criteria against it (Hermes bug 4 fix) |
| `status` | `active \| waiting \| done \| cancelled \| paused` |
| `source` | `user` (user-set, always wins) \| `agent` (self-set) |
| `linked_task_ids` | Kanban card ids this goal is about (JSON array) |
| `subgoals`, `gates` | User-added criteria; gates ALL must pass before the judge may declare done (JSON arrays) |
| `max_turns`, `turns_used` | Turn budget, default 20 |
| `created_at`, `updated_at`, `last_verdict`, `last_reason`, `last_response_snippet` | Audit trail of the last judge run |
| `consecutive_stalled`, `consecutive_transport_failures`, `consecutive_parse_failures` | Counters driving pause decisions |
| `judge_outage_alerted` | Whether the operator was alerted about a judge outage |
| `waiting_on`, `waiting_reason`, `waiting_until` | Wait barrier (`wait` parks the goal here) |
| `pending_human_decisions` | Blockers needing a human (JSON array) |
| `revision` | Row revision counter |

Operator CLI: `scripts/goal-admin.mjs` (`set-user-goal / get / list / clear`).

### Tool actions

| Action | What it does |
|---|---|
| `get` | Returns the current goal for the session, or `{"goal": None}`. The tool description tells the agent: "At the start of every turn, call `get`; if a goal is active, work its next step." |
| `create` | `objective` + `acceptance_criteria` + `verification` + optional `task_ids` / `max_turns`. The declaration IS the inference — the agent infers the goal from the ask and states it. Never overwrites a user-set goal. |
| `link` | Attach kanban card ids to the goal. |
| `complete` | `evidence` (what proves the criteria are met). Runs the completion audit; refuses when the verdict is not DONE, so the agent cannot wave its own goal through. |
| `wait` | Parks the goal on a barrier: `on` = subagents \| process \| seconds \| user, plus `reason`. |
| `resume` | Lifts a wait and re-activates the goal. |
| `clear` | Deletes the goal row. |
| `list` / `search` | **Being added** — list/search goals across sessions (Muse mirror). |
| `update` | **Being added** — edit goal text / criteria / verification. |
| `set_status` | **Being added** — `active` / `completed` (Muse mirror). |
| `create_entry` / `delete_entry` | **Being added** — progress-log entries on a goal (Muse mirror). |
| `delete` | **Being added** — delete a goal (Muse mirror; `clear` is the existing session-scoped equivalent). |

Cron sessions are refused: `create` from a `cron_*` session returns
"cron runs are one-shot and have no goal loop".

### Gating — on by default, opt-out NOT yet implemented

The spec (§4.6) called for ON by default for agents that have a goal, with
an explicit opt-out (the fix for Hermes bug 6, off-by-default). Current
state: the plugin has an `enabledAgents` allowlist in its config; an empty
list means **all agents** — and it is currently installed gateway-wide, so
the mechanism is on for every agent. That is the "on by default" half.

**Flag:** an explicit per-agent opt-out does not exist yet. There is no
`disabledAgents` / `goals.agent_tool: false` flag; the only control is the
allowlist (opt-in list), which inverts the intended default when it is
non-empty. Adding an explicit opt-out is an open item (§f).

### User-set goal wins

A user-set goal always wins and cannot be replaced by the agent's `create`
— verified live: an agent `create` against a user-set goal is refused
("the current goal was set by the user…") and the goal is unchanged.
Den sets the goal via the operator CLI (`goal-admin.mjs set-user-goal`),
which records `source="user"` and the original ask in `user_ask`.

## (c) Judge

### Trigger — decided: agent_end + heartbeat re-assertion + hourly supervisor audit

The spec (§4.3) left the judge trigger open with options (a) agent-called,
(b) scheduled job, (c) heartbeat. The decision, made at build time:

1. **`agent_end` hook — BUILT and verified live.** The Judge runs at EVERY
   turn-end, agent goals included (Hermes judged only user goals per turn).
   Verdicts: `done | continue | blocked | wait`. On `continue` the plugin
   pushes a continuation prompt into the idle session via agentTurn
   (`openclaw agent --session-key … --message …`, retry on "active run"
   up to 3x). The push IS the wake.
2. **`heartbeat_prompt_contribution` — DECIDED, NOT YET IMPLEMENTED.** The
   SDK (OpenClaw 2026.11.2) exposes this hook: a plugin can prepend/append
   context to heartbeat prompts. The design is for the `goal` plugin to
   re-assert the active goal into every heartbeat prompt, so a heartbeat
   tick always carries the goal back into the turn. Today the re-assertion
   depends only on the tool description telling the agent to call `get` at
   the start of every turn. Do not claim the hook contribution exists until
   it is registered and observed.
3. **Hourly supervisor cron audit — DECIDED, NOT YET BUILT.** A cron job
   (one per hour) reads the registry + the board, finds goals that are
   active but stuck — no turns used recently, no push delivered, or a
   `blocked` verdict with no human decision recorded — picks the next
   UNBLOCKED card linked to the goal, and dispatches a subagent via
   agentTurn. This is the audit layer the per-turn judge cannot provide:
   the judge only runs when a turn ends, so a goal that never gets a turn
   (idle session, heartbeat frozen, push failing) is invisible to it.

### Why this choice

- **No supported in-process LLM call for tool handlers.** The SDK exposes
  no `llm.complete` to tool handlers (`llm.complete` appears only in
  plugin-command context). So the Judge cannot be an in-process call; it is
  a separate one-shot model call via `openclaw capability model run`
  (default model `openai/gpt-6.1-sol`, 120s timeout — the call takes
  ~60–70s on the loaded VM; the `agent_end` hook is fire-and-forget so the
  Judge may run past the ~30s hook budget).
- **Not agent-called judge alone** (spec option a): relying on the agent to
  remember to judge itself is the weakest option — it is exactly the
  failure mode the Judge exists to prevent.
- **Not a scheduled judge job alone** (spec option b): a job that only runs
  the judge still leaves the per-turn audit gap, and a job that nudges the
  agent was the removed mistake (the tony-goal-nudge inference job).
- **The supervisor audit is the backstop, not the mechanism.** The
  mechanism is reactive (turn-end Judge + push). The audit exists only to
  catch goals the reactive path never sees.

### Judge behaviour (built)

- **Separate model, strict auditor.** Parses
  `{"verdict": "done|continue|blocked|wait", "reason": ...}`. DONE requires
  concrete evidence, never a bare claim. `complete` with weak evidence is
  refused; with strong evidence it completes.
- **Stall detector.** Word-set Jaccard ≥ 0.85 between consecutive replies
  counts as stalled; pause after **5** stalled turns. Verified by test
  (same reply 5x → paused at the 5th; varied replies keep the counter at 0).
- **Judge-outage pause.** After **3** consecutive transport failures the
  goal pauses ("goal judge unreachable 3 turns in a row — goal paused").
  Verified live. This is the Hermes bug 3 fix: never run unaudited forever.
- **Turn budget.** Default **20** turns (`max_turns`); the hook counts turns
  used (Tony 1/20, Monica 2/20 observed live).
- **Complete-with-audit.** `complete` runs the audit and refuses when the
  verdict is not DONE.
- **Criteria checked against the original user ask.** The judge prompt
  carries `user_ask` alongside the agent-written criteria and instructs the
  judge to refuse DONE when the criteria are weaker than the ask (Hermes
  bug 4 fix). Verified by unit test and live (Judge refused DONE on weak
  evidence).

### Operational notes (from the build report)

- Do NOT use `openclaw plugins reload goal` (or `goal-tool`) to load new
  code. The plugin host waits only 5s to drain, but the Judge takes ~60s
  and the push takes minutes — the reload fails with "Previous plugin
  cleanup failed" and can leave the plugin retired. Load new code with a
  **gateway restart**.
- Judge model: `openai/gpt-6.1-sol` (default). The free deepseek model is
  monthly-limit-exhausted until ~Dec 3, 2026; switch `judgeModel` to
  `opencode-go/deepseek-v4.1-flash` when the limit resets.
- The Judge is flaky when the gateway is unresponsive (a `judge_unavailable`
  verdict — "Unexpected end of JSON input" — was observed when the gateway
  shut down mid-call). The outage counter + pause handle this, but gateway
  flakiness is the root cause.

## (d) The 6 Hermes bugs — how each is fixed (or not)

From spec §3, verified against the Hermes code 2026-11-15.

| # | Hermes bug | OpenClaw fix | Status |
|---|---|---|---|
| 1 | Goal dies at context compression — flat `goal:<session_id>` lookup, no parent walk | Registry keyed to the stable session KEY (`agent:<id>:main`), not a rotating session id | **Fixed by design.** Live compaction NOT yet verified — no actual compaction has been observed with a goal set |
| 2 | Agent goals have no per-turn judge and no turn budget — can run indefinitely | Judge runs at EVERY turn-end, agent goals included; stall detector (Jaccard ≥ 0.85, pause after 5 stalled turns); turn budget 20 | **Fixed and verified** (judge verdicts live; stall pause by test) |
| 3 | Judge unreachable = never pause (fails open to `continue`, single operator alert) | After 3 consecutive transport failures the goal pauses and surfaces as a blocker | **Fixed and verified live** |
| 4 | Self-graded acceptance criteria — agent writes them, audit checks them | `user_ask` stored alongside the criteria; judge prompt refuses DONE when criteria are weaker than the ask | **Fixed and verified** (unit test + live refusal on weak evidence) |
| 5 | Stop-check plugin broken on Linux — symlink to a macOS path, does not load | **Not fixed — known limitation.** There is no turn-end stop-check in OpenClaw (no hook enforces "cannot end a turn while a card is unattended"). Closest mechanisms: the system-prompt guidance (agent checks itself) + the judge returning BLOCKED for an unattended card. Recorded as a limitation, not a solved problem | **Open** |
| 6 | Goal tool off by default — silently inactive unless opted in | Enabled gateway-wide (empty allowlist = all agents) | **Half fixed.** "On by default" holds; explicit per-agent opt-out does NOT exist yet (§b, §f) |

## (e) Acceptance criteria — status

Adapted from spec §5, with honest live status copied from the build report
(`~/workspace/goal-plugin/BUILD-REPORT.md`, 2026-11-16 end of day). Do not
claim unverified items as verified.

1. **Goal tool callable by an agent — NOT verified live.** Tool built +
   loaded (appears in the gateway's 21-plugin list), but no live agent call
   has succeeded yet; blocked by gateway restarts/unresponsiveness. Handler
   + registry + complete-refuse/complete verified by unit tests and dry-run.
2. **User-set goal cannot be overwritten — VERIFIED live.**
3. **Goal survives compaction/rotation — verified by design + unit test**
   (keyed to stable sessionKey). **Not verified by an actual live compaction.**
4. **Stall detector pauses a non-progressing goal — VERIFIED** (test; 5x
   same reply → paused; varied replies → counter stays 0).
5. **Judge outage pauses after N failures — VERIFIED live** (mechanism).
6. **Criteria checked against the original user ask — VERIFIED by unit test**
   (judge prompt carries the user ask + the rule that weaker criteria mean
   NOT done) and live (Judge refused DONE on weak evidence).
7. **Goal text is NOT in any file — PARTIAL.** Live state is in the registry
   (`goal.db`); no GOAL_STATE.md exists. BUT Tony's generated AGENTS.md
   still has a standing "## GOAL — public release ready, first $10K MRR"
   section (from the AGENTS.md generator). Removing it requires editing the
   generator (Mallow repo) — out of scope; flag as a parent decision.
8. **No inference job exists to nudge the agent — HOLDS** (no such job
   created; the push comes from the turn-end hook, not a cron job). Note:
   the hourly supervisor audit in §c(3) is an audit job, not an inference
   nudge — it reads the registry and dispatches only when a goal is stuck.
   It is decided, not yet built; when built it must be listed here so this
   criterion stays checkable.
9. **Heartbeat continues an active goal — NOT verifiable yet** (heartbeat was
   frozen; the mechanism today is the tool description telling the agent to
   call `get` at the start of every turn). The `heartbeat_prompt_contribution`
   hook (§c(2)) is the designed fix; not yet implemented.
10. **Tony and Monica both have the mechanism, each with their own goal —
    goals set for both (active); mechanism installed gateway-wide;
    per-criterion verification as listed above.** Tony
    (`agent:product-lead-agentpod:main`): "Make Mallow public release ready,
    first $10K MRR" [active, user-set, turn 1/20]. Monica
    (`agent:product-lead-vibebrowser:main`): "Ship VibeBrowser public
    release ready, first $10K MRR" [active, user-set, turn 2/20].

## (f) Open items

1. **Goal tool not yet seen live.** The `goal-tool` plugin loads, but no
   live agent turn has called the `goal` tool (gateway restarts aborted the
   test turns). Next step: after a gateway restart, send a live agentTurn
   asking the agent to call `goal(action="get")` and read back the result.
2. **Push not yet verified.** The push was attempted several times
   (`push_failed` in the log) and failed each time because the gateway was
   down/unresponsive when the agentTurn ran. A successful push is not
   verified.
3. **Live compaction not verified.** The registry survives compaction by
   design (stable session key); no live compaction with a goal set has been
   observed. Next step: set a test goal, compact, call `get`.
4. **`heartbeat_prompt_contribution` not yet implemented.** Decided (§c(2));
   needs a plugin change + gateway restart + live observation of a heartbeat
   carrying the goal.
5. **Hourly supervisor audit not yet built.** Decided (§c(3)); needs a cron
   job + dispatch path. Must not become an inference nudge job — it audits
   and dispatches only stuck goals.
6. **Explicit opt-out not implemented.** Gating is allowlist-only; empty =
   all agents. Add a per-agent opt-out flag before the mechanism is relied
   on for agents that should not have it.
7. **Tony's generated AGENTS.md still has a GOAL section.** From the Mallow
   AGENTS.md generator, not from this plugin. Removing it requires editing
   the generator (Mallow repo) — out of scope for this plugin; parent
   decision. Until then, criterion §e(7) stays PARTIAL.
8. **Built-in OpenClaw goal tools exist — pivot option.** OpenClaw 2026.11.2
   has built-in `get_goal / create_goal / update_goal`
   (`src/agents/tools/goal-tools.ts`), which ARE visible to the agent. The
   spec's "OpenClaw has NO goal tool" was wrong. If the custom `goal` tool
   still does not appear after the next gateway restart, pivot the tool
   surface to the built-in tools and have the Judge read OpenClaw's
   session-goal store instead of `goal.db`.
9. **Stop-check (Hermes bug 5) has no OpenClaw equivalent.** Known
   limitation (§d, bug 5). No turn-end enforcement that a card the agent
   owns is attended; only guidance + judge BLOCKED verdicts.

## Diagram

`diagrams/gen-goal-mechanism-diagrams.py` — function
`openclaw_goal_plugin_diagram()` draws the loop (agent → goal tool →
registry → turn ends → Judge → push → next turn, with the heartbeat
re-assertion and the hourly supervisor audit). Rendered PNGs go to the
Notion page; the repo keeps only the generator.
