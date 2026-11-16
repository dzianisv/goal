# How Muse does it — corrected

**Status: corrected 2026-11-16.** The earlier version of this page stated
Muse's goal mechanism as fact. It was not fact — it was a guess assembled
from a product doc, a system-prompt quote, and a third-party comment.
A research pass on 2026-11-15 checked it against public sources and found
most of it unverifiable. This page now says only what the evidence supports.

Full report: `~/workspace/research_notes/muse-goal-mechanism-evidence-20261115-1423/report.md`
(research date 2026-11-15; read the report for the full source list).

## Verdict

| Claim | Verdict |
|---|---|
| Durable goal saved in the Goals tab | **Confirmed** — official (Meta Newsroom 2026-09-08; Help Center) + tested live by an independent tester 2026-10-05 |
| Background work on a goal happens on a schedule / in response to events | **Confirmed** — official docs; in practice a goal behaves as a scheduled task (daily, every 2 hours in the observed test) |
| System-prompt instruction: create a goal when the user shares an enduring aspiration, even without saying "goal" | **No public evidence** — not in official docs, not in leaked-prompt reporting. A goal-creation *skill* exists in the leaked VM files, but its text on this point was never publicly quoted |
| Hourly supervisor re-reads the goal, picks the next highest-priority unblocked card, dispatches a subagent, updates a board, repeats | **No public evidence** — no source describes this. Hourly jobs evidenced are for people/memory pages, feed pulses, and a shopping loop — never for goal cards |
| No per-session goal tool | **Contradicted for Muse Code; unverifiable for personal Muse** — Muse Code documents `get_goal` / `create_goal` / `update_goal` / `report_progress`, session-scoped. Personal Muse shows no such tool publicly |
| No Judge model | **No "Judge" in Meta Muse material.** Oversight is Sentinel (a permission/egress authority, not a goal grader). Muse Code has a requirement-by-requirement completion check gating `update_goal` |
| No post-turn hook | **Contradicted for Muse Code; unverifiable for personal Muse** — Muse Code queues a follow-up after a turn finishes. Personal Muse: no public doc |
| Direct Reddit / Hacker News / Stack Overflow threads on Muse goals | **None found** — only second-hand summaries citing r/MetaAI, r/singularity, r/LocalLLaMA |

## What is confirmed

- Muse is **closed source** — Meta published design/safety blog posts, not code or a technical paper on the goal mechanism.
- Once a person shares a goal, Muse "helps them develop a personalized plan and coordinate their time and resources, then advances the work on its own" (Meta Newsroom, 2026-09-08). Help Center wording is "goals that you have set" — user-set, which leans *against* automatic creation from an unspoken aspiration.
- The documented background mechanism is **user-set schedules** ("You can ask Muse to remind you about anything at a specific time… run recurring tasks on a schedule"), not an hourly supervisor loop.
- A tested goal ran as a **scheduled task** in the Goals tab ("Watch scheduled — checking … every 2 hours"). One user guide states the opposite of an autonomous loop: "A goal organizes the work but won't run itself, so ask Muse to schedule check-ins."
- Subagents exist generally; the Kanban board in user reports is a **user-invented artifact built on demand**, not a built-in goal mechanism. Spaces (Nov 6, 2026) adds project boards updated from connected apps, with no supervisor-picks-card mechanism described.

## The likely conflation

The "hourly supervisor + Judge grades goal completion" shape **does exist publicly — in Hermes/AgentPod**, a third-party system that explicitly copied Muse Code's goal lifecycle
("398 Lines So the Agent Defines Done First: The Hermes goal Tool, Copied From Muse",
agentlabs.cc). That is the plausible origin of the earlier description on this page,
not Meta's public Muse documentation. Do not present the Hermes shape as Muse's.

## What this means for the OpenClaw plugin

The plugin's shape (session goal tool + registry + per-turn Judge + push) is
**not a copy of personal Muse's internals** — those are unverified. It is a
port of the **Hermes** goal mechanism, whose session-goal tool shape matches
**Muse Code** (`get_goal` / `create_goal` / `update_goal` / `report_progress`,
session-scoped, with a post-turn follow-up queue). The durable-goal surface
it mirrors is Muse's live `user_goal.*` tool list (create / list / search /
get / update / set_status / create_entry / update_entry / delete_entry /
delete). See [openclaw-goal-plugin-design.md](openclaw-goal-plugin-design.md).

## Sources (key)

- Official, verified live: https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/ (2026-09-08)
- Official, index: https://www.meta.com/help/superintelligence/2225571704857152/ ; https://www.meta.com/help/superintelligence/1484325780075655/
- Tested, verified live: https://metamuseai.site/muse/goals-feed-ideas/ (tested 2026-10-05)
- Leaked-files review: https://futuresociety.ch/muse-findings/
- Muse Code goal tools, index: https://dev.meta.ai/docs/muse-code/interactive ; https://github.com/souta-lab/pi-muse/blob/HEAD/README.md
- Third-party Judge / hourly-supervisor system: https://www.agentlabs.cc/blog/how-agentpod-is-built-by-an-agentic-team-on-hermes/
- Spaces: https://techcrunch.com/2026/11/06/meta-introduces-spaces-a-new-way-to-collaborate-with-your-muse-agent/
- Closed source: https://personalagentbench.com/is-meta-muse-open-source/

Diagram: drawn by `diagrams/gen-goal-mechanism-diagrams.py` (PNG on the Notion page).
The Muse diagram in that generator still shows the OLD, uncorrected loop —
it is kept for the record and must not be presented as verified.
