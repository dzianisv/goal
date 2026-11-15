# How Muse does it

From the design description + Muse's goal docs (`docs/goals.md`, the system prompt). NOT from Muse internals — Muse is closed source, there is no public code to read. Do not read more into it.

## Where this comes from (Den asked)

There is no article, no Reddit post, and no shared source code. Muse is closed source — nothing to read. The mechanism above comes from three places:

1. **`docs/goals.md`** — Muse's product doc. It describes goal management: goals are durable milestones, maintained and managed by Muse, created/read/updated/logged with the goal tools. It says real background work on a goal happens only through scheduled jobs.
2. **The system prompt** — the instruction quoted below ("create a goal when the user shares an enduring aspiration..."). This is the "automatic" part. It is in Muse's own system prompt, which I can read.
3. **Hermes's code** — `agent/prompt_builder.py` line 240 calls its design "Muse-style goal ownership: the model declares the session goal itself". That is Hermes's developers describing the pattern they copied. Second-hand, not Muse source.

That is all the evidence there is. Do not read more into it.

## The goal is set automatically — how?

There is no special goal tool and no per-session goal. The "automatic" part is an instruction in the system prompt, plus the goal tools.

The system prompt tells Muse:

> Create a goal when the user shares an enduring aspiration, a commitment with a timeframe, progress, or a setback — even when they never say "goal".

So when Den states what he wants in conversation, Muse creates a goal from it. No set-goal command from Den. Den states what he wants — product owner, not goal-setter.

The agent saves it as a DURABLE goal (Goals tab) with the goal tools — a milestone, not a per-session goal. `docs/goals.md` describes it: goals are durable milestones, maintained and managed by Muse. Real background work on a goal happens only through scheduled jobs. A goal by itself runs nothing.

## What Muse does NOT have (unlike Hermes)

- No per-session goal tool. Hermes has `goal` (create / get / complete / wait) with a per-session registry. Muse has no equivalent.
- No judge. Hermes runs `judge_goal` after a turn to ask "is the goal DONE?". Muse has no per-turn goal check.
- No per-turn goal mechanism at all. The goal is a durable milestone; it stays alive because the system-prompt instruction creates it and the hourly supervisor re-asserts it.

The behavior looks similar to Hermes (the goal appears without a set-goal command) but the mechanism is different. Do not call it "the same auto-inference as Hermes" — Hermes infers a per-session goal with a tool call and a judge; Muse creates a durable goal from a system-prompt instruction.

Where the "Muse-style" phrase comes from: Hermes's own code (`agent/prompt_builder.py` line 240) calls its design "Muse-style goal ownership: the model declares the session goal itself". That is Hermes's developers describing the pattern they copied. It is second-hand evidence about Muse, not Muse source.

## The loop — same shape as Hermes, different machinery

Goal → work → check → repeat. Hermes checks with a Judge model per turn; Muse checks by looking for the next unblocked card each hour. No Judge.

1. The system-prompt instruction creates the goal from the conversation (see above).
2. A supervisor run starts (hourly). It re-asserts that goal.
3. The supervisor picks the next highest-priority UNBLOCKED card. The agent does not decide whether to work.
4. A subagent builds the picked card. One subagent per task.
5. The subagent updates the board.
6. The supervisor run ends.
7. CHECK — is there a next unblocked card? If yes, next hour the supervisor runs again (loop back to step 2). If no, the goal is done (or blocked) — the loop pauses until there is work.

No idle trigger. Hourly schedule.

Diagram: drawn by `diagrams/gen-goal-mechanism-diagrams.py` (PNG on the Notion page).
