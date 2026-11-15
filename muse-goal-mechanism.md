# How Muse does it

From the design description + Muse's goal docs (`docs/goals.md`, system prompt, `goal-mechanism-spec.md` lines 9/50). NOT from Muse internals. Do not read more into it.

## The goal is set automatically

Muse infers the goal from the project/conversation and declares it itself. No set-goal command from Den. Den states what he wants in conversation — product owner, not goal-setter.

This is "Muse-style goal ownership: the model declares the session goal itself." The same auto-inference as Hermes. (An earlier draft wrongly said "Den sets the project goal once." That line exists nowhere in the source. It was invented and removed.)

## The loop

1. Muse sets the goal automatically (see above).
2. An hourly supervisor re-asserts that goal each run and picks the next highest-priority UNBLOCKED card. The agent does not decide whether to work.
3. A subagent builds the picked card. One subagent per task.
4. The subagent updates the board.
5. Next hour, the supervisor runs again.

No idle trigger. Hourly schedule.

## What Muse's goal docs say

Goals are durable milestones. Muse creates and manages them. A goal is created when the user shares an enduring aspiration, a commitment with a timeframe, progress, or a setback — even when they never say "goal". Real background work on a goal happens only through scheduled jobs. A goal by itself runs nothing.

Diagram: [diagrams/muse-goal-mechanism.mmd](diagrams/muse-goal-mechanism.mmd).
