#!/usr/bin/env python3
"""Goal mechanism diagrams — Hermes and Muse, in DEN'S SKETCH style.
Den rejected both earlier styles (big wide colored nodes; sequence
diagrams). His sketch (workspace/user/media_library/image/image-2.png)
is the reference: thin rounded boxes, plain black-on-white, small boxes,
a vertical message flow, a Tools box on the side with an arrow, and the
open question at the bottom answered: what injects the goal back, and when.

Facts (verified from code, 2026-11-15):
- Inference (Hermes): the MAIN session infers the goal. The agent itself,
  in the same turn as the user message, declares it with
  goal(action="create", objective, acceptance_criteria). No background
  API call infers the goal. The only auxiliary model call is judge_goal,
  which only checks whether the goal is DONE.
- Judge (Hermes): judge_goal is a separate auxiliary model call
  (agent.auxiliary_client.call_llm). It runs in the post-turn hook
  (_maybe_continue_goal_after_turn → evaluate_after_turn), AFTER the
  turn ends — after the AI's final message, when the user already has
  the response. It asks only "is the goal DONE?" — done / continue /
  blocked / wait. If continue, the hook enqueues a continuation prompt
  (next_continuation_prompt) which starts the next turn. It runs per
  turn ONLY for USER-set goals. Agent (self-inferred) goals SKIP the
  judge — evaluate_after_turn returns early with verdict "continue",
  reason "heartbeat", and the continuation is enqueued directly.
- Injection (feeding the goal back): (1) heartbeat tick —
  next_continuation_prompt feeds the goal back as a user-role message;
  (2) idle-wake — the barrier-wake chore re-pokes an active goal with
  no turn for idle_wake_seconds (default 900s = 15 min). Both re-assert
  the EXISTING goal; neither infers a new one.
- Hermes source: /home/engineer/.hermes/hermes-agent/
  tools/goal_tool.py, hermes_cli/goals.py, agent/prompt_builder.py:240.
- Muse: NO source code (closed). The "automatic" goal comes from an
  instruction in the system prompt: create a goal when the user shares
  an enduring aspiration, a commitment, progress, or a setback — even
  without the word "goal". The agent saves it as a DURABLE goal (Goals
  tab) with the goal tools. No per-session goal tool. No judge. The
  hourly supervisor re-asserts the goal each run. Evidence: docs/goals.md
  + the system prompt + Hermes's "Muse-style goal ownership" comment
  (second-hand, from Hermes's code, not Muse's). Do not read more into it.

Hand-built SVG, standard library only.
Render: chrome-headless-shell --force-device-scale-factor=3 (native 3x;
fall back to native 2x + PIL Lanczos upscale to 3x). Never 1x->3x.
Repo keeps only this generator — never PNG/SVG. Mermaid was removed:
GitHub's auto-layout can't match the sketch style. Rendered PNGs go to Notion.
"""
import os

W = 2800
MARGIN = 60
C = {
    "ink": "#111111", "label": "#555555", "muted": "#666666",
    "box": "#ffffff", "border": "#111111",
    "hl_border": "#111111", "hl_fill": "#f2fbf2",
    "note_border": "#111111", "note_fill": "#ffffff",
    "warn_border": "#111111", "warn_fill": "#ffffff",
    "edge": "#111111",
}
TITLE = 52
SUBTITLE = 30
BOX_T = 40        # box title text
BOX = 36          # box body text
SMALL = 30        # note text
NOTE_T = 32
LEGEND = 26
LINE_H = 46


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Svg:
    def __init__(self):
        self.parts = []

    def rect(self, x, y, w, h, fill, stroke, sw=2):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')

    def dashed_rect(self, x, y, w, h, fill, stroke, sw=2):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" '
            f'stroke-dasharray="12 9"/>')

    def text(self, x, y, s, size, color, bold=False, anchor="middle"):
        b = ' font-weight="700"' if bold else ''
        self.parts.append(
            f'<text x="{x}" y="{y}" font-family="Inter, system-ui, sans-serif" '
            f'font-size="{size}" fill="{color}" text-anchor="{anchor}"{b}>{esc(s)}</text>')

    def line(self, x1, y1, x2, y2, sw=3, dashed=False):
        d = ' stroke-dasharray="12 9"' if dashed else ''
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C["edge"]}" '
            f'stroke-width="{sw}"{d}/>')

    def arrow(self, x1, y1, x2, y2, sw=3, dashed=False):
        d = ' stroke-dasharray="12 9"' if dashed else ''
        self.parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{C["edge"]}" '
            f'stroke-width="{sw}"{d} marker-end="url(#arrow)"/>')

    def down_arrow(self, cx, y1, y2, sw=3):
        self.arrow(cx, y1, cx, y2, sw=sw)

    def box(self, x, y, w, h, lines, title=None, bold_border=False,
            fill=None):
        self.rect(x, y, w, h, fill or C["box"], C["border"],
                  4 if bold_border else 2)
        cx = x + w // 2
        if title is not None:
            n = len(lines)
            total = (n + 1) * LINE_H
            yy = y + (h - total) // 2 + 34
            self.text(cx, yy, title, BOX_T, C["ink"], bold=True)
            yy += LINE_H
            for ln in lines:
                self.text(cx, yy, ln, BOX, C["ink"])
                yy += LINE_H
        else:
            n = len(lines)
            total = n * LINE_H
            yy = y + (h - total) // 2 + 34
            for i, ln in enumerate(lines):
                self.text(cx, yy, ln, BOX, C["ink"], bold=(i == 0 and n > 1 and False))
                yy += LINE_H
        return y + h

    def header(self, title, subtitle):
        self.text(W // 2, 78, title, TITLE, C["ink"], bold=True)
        self.text(W // 2, 132, subtitle, SUBTITLE, C["label"])
        return 170

    def legend(self, y, lines):
        y += 16
        for ln in lines:
            self.text(W // 2, y + 24, ln, LEGEND, C["muted"])
            y += 32
        return y + 12

    def build(self, out_path):
        H = self._h
        header = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}">\n'
            '<defs>'
            '<marker id="arrow" markerWidth="13" markerHeight="11" '
            'refX="11" refY="5.5" orient="auto">'
            f'<polygon points="0 0, 13 5.5, 0 11" fill="{C["edge"]}"/></marker>'
            '</defs>\n'
            f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>\n')
        svg = header + "\n".join(self.parts) + "\n</svg>\n"
        with open(out_path, "w") as f:
            f.write(svg)
        print(f"SVG written: {out_path} ({len(svg)} bytes), canvas {W}x{H}")
        return out_path


def note_box(s, x, y, w, h, title, lines):
    s.rect(x, y, w, h, C["note_fill"], C["note_border"], 2)
    s.text(x + 30, y + 48, title, NOTE_T, C["ink"], bold=True, anchor="start")
    yy = y + 48 + 44
    for ln in lines:
        s.text(x + 30, yy, ln, SMALL, C["ink"], anchor="start")
        yy += 40
    return y + h


# ---- Hermes: the whole agentic loop ----

def hermes_diagram(out_path):
    s = Svg()
    y = s.header(
        "How the goal works in Hermes — the whole loop",
        "Read from the code: /home/engineer/.hermes/hermes-agent/  ·  verified 2026-11-15")
    cx = W // 2

    # OpenClaw (top, as in the sketch)
    y = s.box(cx - 800, y, 1600, 110, ["OpenClaw"]) + 40

    # Profiles row
    y0 = y
    s.box(cx - 800, y0, 760, 110, ["Profile: agent1"])
    s.box(cx + 40, y0, 760, 110, ["Profile: agent2"])
    y = y0 + 110 + 40

    # Sessions under agent1
    s.box(cx - 780, y, 360, 90, ["Session 1"])
    s.box(cx - 400, y, 360, 90, ["Session 2"])
    y = y + 90 + 30

    # ---- THE TURN (the loop) ----
    # Flow column, centred. Tools box on the left, notes on the right.
    fx = cx - 100   # flow centre
    fw = 760
    fx0 = fx - fw // 2
    gap = 34

    # Turn starts
    turn_y = y
    s.box(fx0, y, fw, 84, ["Turn starts — user message arrives"])
    turn_cy = y + 42
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    # AI message
    ai_y = y
    s.box(fx0, y, fw, 84, ["AI message"])
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Goal inference — green, bold border. THE point where the goal is born.
    inf_y = y
    s.box(fx0, y, fw, 150,
          ["★ Goal inferred HERE",
           "no goal? agent calls goal(create)",
           "objective + acceptance_criteria"],
          bold_border=True, fill=C["hl_fill"])
    y = inf_y + 150
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Tool calls
    calls_y = y
    s.box(fx0, y, fw, 84, ["Tool calls — goal · read · write"])
    calls_cy = y + 42
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Tool results
    s.box(fx0, y, fw, 84, ["Tool results come back"])
    y += 84
    # Turn ends
    s.down_arrow(fx, y, y + gap)
    y += gap
    end_y = y
    s.box(fx0, y, fw, 84, ["Turn ends"])
    end_cy = y + 42
    y = end_y + 84

    # Tools box on the left, aligned with Tool calls
    tools_x, tools_w = 60, 380
    tools_y = calls_cy - 120
    tools_h = 240
    s.rect(tools_x, tools_y, tools_w, tools_h, C["box"], C["border"], 2)
    s.text(tools_x + tools_w // 2, tools_y + 52, "Tools:", BOX_T, C["ink"], bold=True)
    for i, t in enumerate(["goal", "read", "write"]):
        s.text(tools_x + tools_w // 2, tools_y + 52 + (i + 1) * LINE_H, t, BOX, C["ink"])
    s.arrow(tools_x + tools_w + 4, calls_cy, fx0 - 6, calls_cy)

    # Inference note, right of the green box
    note_x = fx0 + fw + 80
    note_w = 900
    s.rect(note_x, inf_y - 10, note_w, 180, C["hl_fill"], C["border"], 2)
    s.text(note_x + 30, inf_y + 34, "In the main session, in the same turn", BOX_T,
           C["ink"], bold=True, anchor="start")
    for i, ln in enumerate([
        "The agent itself infers the goal and",
        "declares it with this call.",
        "No background API call infers the goal.",
    ]):
        s.text(note_x + 30, inf_y + 34 + (i + 1) * 40, ln, SMALL, C["ink"],
               anchor="start")

    # ---- JUDGE (post-turn hook, IN the main flow) ----
    # The Judge is a separate auxiliary model call. It runs AFTER the turn
    # ends — after the AI's final message, when the user already has it.
    # For USER goals it asks "is the goal DONE?"; for AGENT goals there is
    # no Judge — the heartbeat just continues.
    y = y + 50
    s.down_arrow(fx, y - 50, y)
    jx, jw = fx - 1000, 2000
    judge_y = y
    judge_h = 260
    s.rect(jx, judge_y, jw, judge_h, C["box"], C["border"], 2)
    jcx = jx + jw // 2
    s.text(jcx, judge_y + 52,
           "POST-TURN — Judge runs (a separate auxiliary model call)",
           BOX_T, C["ink"], bold=True)
    for i, ln in enumerate([
        "Runs AFTER the AI's final message — the user already has the response.",
        "USER goal: auxiliary model asks 'is the goal DONE?' → done / continue / blocked / wait",
        "AGENT goal: NO judge — heartbeat just continues",
        "If continue → continuation prompt is enqueued → next turn starts",
    ]):
        s.text(jcx, judge_y + 52 + (i + 1) * 46, ln, BOX, C["ink"])
    judge_cy = judge_y + judge_h // 2
    y = judge_y + judge_h

    # ---- LOOP BACK (right side): continuation → next turn ----
    loop_rx = 2700
    s.line(jx + jw, judge_cy, loop_rx, judge_cy)
    s.line(loop_rx, judge_cy, loop_rx, turn_cy)
    s.arrow(loop_rx, turn_cy, fx0 + fw + 6, turn_cy)
    s.text((fx0 + fw + loop_rx) // 2, turn_cy - 22, "continuation prompt → next turn",
           SMALL, C["muted"])

    # ---- INJECTION note: what feeds the goal back in ----
    y = y + 50
    inj_x, inj_w = cx - 1000, 2000
    inj_y = y
    s.rect(inj_x, inj_y, inj_w, 260, C["box"], C["border"], 2)
    s.text(cx, inj_y + 52,
           "What feeds the goal back in? (the loop above)", BOX_T, C["ink"], bold=True)
    for i, ln in enumerate([
        "1 · Heartbeat tick — next_continuation_prompt feeds the goal back as a user-role message.",
        "2 · Idle-wake — the barrier-wake chore re-pokes an active goal after 15 min idle (idle_wake_seconds = 900).",
    ]):
        s.text(cx, inj_y + 52 + (i + 1) * 46, ln, BOX, C["ink"])
    s.text(cx, inj_y + 52 + 3 * 46 + 12,
           "Both re-assert the EXISTING goal. Never inferred in the background.",
           BOX, C["ink"], bold=True)
    y = inj_y + 260

    # Bottom notes: override (left) + watch out (right)
    y = y + 50
    NW = 1290
    NH2 = 48 + 44 + 6 * 40 + 16
    note_box(s, MARGIN, y, NW, NH2,
             "Side note — /goal is an override, not the flow",
             ["Den can set the goal with /goal — a user-set goal always wins,",
              "the agent cannot replace it. That is an override, not the flow."])
    note_box(s, MARGIN + NW + 24, y, NW, NH2,
             "WATCH OUT — known bugs in Hermes (do not copy)",
             ["Goal dies at context compression — flat goal:<session_id> lookup, no parent walk.",
              "Agent goals have no per-turn judge or turn budget — no stall detection.",
              "A dead judge never pauses the goal — it fails open to continue.",
              "The agent grades its own criteria — it writes them, the audit checks them.",
              "Stop-check plugin broken on Linux — symlink to a macOS path, does not load.",
              "Goal tool off by default — the mechanism is silent unless opted in."])
    y += NH2

    y = s.legend(y, [
        "Solid arrow = flow  ·  loop on the right = next turn (continuation prompt feeds the goal back in)",
        "Inside a turn: AI message → tool calls → results, repeated till the agent stops calling tools",
        "Bold green box = the goal, inferred in the main session  ·  plain boxes, black on white, as in Den's sketch",
    ])
    s._h = y
    return s.build(out_path)


# ---- Muse: the same loop, different machinery ----

def muse_diagram(out_path):
    s = Svg()
    y = s.header(
        "How the goal works in Muse — the same loop, different machinery",
        "From the docs + system prompt — NOT from Muse internals (closed source) · do not read more into it")
    cx = W // 2
    fx = cx - 300          # flow centre (board box sits on the right)
    fw = 1200
    fx0 = fx - fw // 2
    gap = 34

    # Goal setup — the "automatic" part (like Hermes's goal inference, but
    # via a system-prompt instruction + a durable goal, not a goal tool).
    s.box(fx0, y, fw, 150,
          ["★ Goal set automatically — system prompt: create a goal when",
           "the user shares an enduring aspiration — even without",
           "the word 'goal'. No set-goal command needed."],
          bold_border=True, fill=C["hl_fill"])
    y += 150
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Durable goal
    s.box(fx0, y, fw, 140,
          ["Agent saves it as a DURABLE goal (Goals tab)",
           "a milestone, not a per-session goal"])
    y += 140
    s.down_arrow(fx, y, y + gap)
    y += gap

    # ---- THE LOOP (same shape as Hermes: work cycle → check → loop back) ----
    # Supervisor run starts
    sup_start_y = y
    s.box(fx0, y, fw, 84, ["Supervisor run starts (hourly)"])
    sup_start_cy = y + 42
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Pick the card (the "check" — is there work?)
    pick_y = y
    s.box(fx0, y, fw, 96,
          ["Picks the next highest-priority UNBLOCKED card"])
    pick_cy = y + 48
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Subagent builds
    build_y = y
    s.box(fx0, y, fw, 96, ["Subagent builds the picked card"])
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Subagent updates the board
    upd_y = y
    s.box(fx0, y, fw, 96, ["Subagent updates the board"])
    upd_cy = y + 48
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Supervisor run ends
    s.box(fx0, y, fw, 84, ["Supervisor run ends"])
    y += 84

    # Board box on the right (like Hermes's Tools box on the left)
    b_x, b_w = fx0 + fw + 220, 640
    b_y = pick_y + 14
    s.rect(b_x, b_y, b_w, 180, C["box"], C["border"], 2)
    s.text(b_x + b_w // 2, b_y + 52, "Board", BOX_T, C["ink"], bold=True)
    s.text(b_x + b_w // 2, b_y + 52 + LINE_H, "the cards", BOX, C["ink"])
    gap_cx = (fx0 + fw + b_x) // 2
    s.arrow(fx0 + fw + 4, pick_cy, b_x - 6, b_y + 95)
    s.text(gap_cx, (pick_cy + b_y + 95) // 2 - 26, "reads", SMALL, C["muted"])
    s.arrow(fx0 + fw + 4, upd_cy, b_x - 6, b_y + 140)
    s.text(gap_cx, (upd_cy + b_y + 140) // 2 - 26, "updates", SMALL, C["muted"])

    # ---- CHECK (like Hermes's Judge, but no separate model) ----
    y = y + 50
    s.down_arrow(fx, y - 50, y)
    jx, jw = fx - 1000, 2000
    check_y = y
    check_h = 240
    s.rect(jx, check_y, jw, check_h, C["box"], C["border"], 2)
    jcx = jx + jw // 2
    s.text(jcx, check_y + 52,
           "CHECK — Is there a next unblocked card?",
           BOX_T, C["ink"], bold=True)
    for i, ln in enumerate([
        "The supervisor looks for the next card each hour. No separate Judge model.",
        "If yes → next hour, the supervisor runs again (loop back).",
        "If no → the goal is done (or blocked) — the loop pauses until there is work.",
    ]):
        s.text(jcx, check_y + 52 + (i + 1) * 46, ln, BOX, C["ink"])
    check_cy = check_y + check_h // 2
    y = check_y + check_h

    # ---- LOOP BACK (right side): next hour → supervisor runs again ----
    loop_rx = 2700
    s.line(jx + jw, check_cy, loop_rx, check_cy)
    s.line(loop_rx, check_cy, loop_rx, sup_start_cy)
    s.arrow(loop_rx, sup_start_cy, fx0 + fw + 6, sup_start_cy)
    s.text((fx0 + fw + loop_rx) // 2, sup_start_cy - 22,
           "next hour — supervisor runs again", SMALL, C["muted"])

    # Bottom note — same loop, different machinery + sources
    y = y + 50
    NW = 2000
    NH = 48 + 44 + 5 * 40 + 16
    note_box(s, (W - NW) // 2, y, NW, NH,
             "Same loop as Hermes — different machinery (Den asked)",
             ["Goal → work → check → repeat. Hermes checks with a Judge model per turn;",
              "Muse checks by looking for the next unblocked card each hour. No Judge.",
              "Sources: (1) docs/goals.md (2) the system prompt (3) Hermes's 'Muse-style' comment.",
              "No article, no Reddit post, no shared source code — Muse is closed.",
              "No per-session goal tool. No per-turn goal check."])
    y += NH

    y = s.legend(y, [
        "Solid arrow = flow  ·  loop on the right = next hour, back to the supervisor run",
        "Same shape as the Hermes diagram: goal → work cycle → check → loop back",
        "Plain boxes, black on white, as in Den's sketch",
    ])
    s._h = y
    return s.build(out_path)


# ---- OpenClaw: Muse-style loop, built for OpenClaw (DESIGN) ----
# Den asked: can we implement what Muse has, for OpenClaw? Yes.
# Muse has no Judge, no goal tool, no post-turn hook — just a
# system-prompt instruction, a durable goal, and an hourly supervisor
# job. OpenClaw already has all the pieces: AGENTS.md (the system
# prompt), cron jobs (the supervisor), the kanban board, agentTurn
# (dispatch a subagent). This diagram is the design: what to build,
# which files, and the implementation plan.

def openclaw_muse_diagram(out_path):
    s = Svg()
    y = s.header(
        "Muse-style goal loop, built for OpenClaw — design",
        "No Judge, no goal tool, no post-turn hook — just an instruction, a durable goal, and an hourly supervisor job")
    cx = W // 2
    fx = cx - 300          # flow centre (board box sits on the right)
    fw = 1200
    fx0 = fx - fw // 2
    gap = 34

    # Goal instruction — in AGENTS.md (the system prompt).
    s.box(fx0, y, fw, 150,
          ["★ AGENTS.md — goal instruction (the system prompt)",
           "When the user shares an enduring aspiration, a commitment,",
           "progress, or a setback — declare it as the goal below."],
          bold_border=True, fill=C["hl_fill"])
    y += 150
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Durable goal — the GOAL section of AGENTS.md.
    s.box(fx0, y, fw, 140,
          ["Durable goal — AGENTS.md GOAL section",
           "The goal text lives here. The supervisor reads it every run."])
    y += 140
    s.down_arrow(fx, y, y + gap)
    y += gap

    # ---- THE LOOP (same shape as Hermes and Muse) ----
    sup_start_y = y
    s.box(fx0, y, fw, 84, ["Supervisor job runs (hourly, OpenClaw cron)"])
    sup_start_cy = y + 42
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    s.box(fx0, y, fw, 84, ["Reads the GOAL from AGENTS.md"])
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    pick_y = y
    s.box(fx0, y, fw, 96,
          ["Reads the board, picks next UNBLOCKED card"])
    pick_cy = y + 48
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    s.box(fx0, y, fw, 96, ["Dispatches subagent via agentTurn"])
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    s.box(fx0, y, fw, 96, ["Subagent builds the picked card"])
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    upd_y = y
    s.box(fx0, y, fw, 96, ["Subagent updates the board (kanban)"])
    upd_cy = y + 48
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    s.box(fx0, y, fw, 84, ["Supervisor job ends"])
    y += 84

    # Board box on the right (kanban DB)
    b_x, b_w = fx0 + fw + 220, 640
    b_y = pick_y + 14
    s.rect(b_x, b_y, b_w, 180, C["box"], C["border"], 2)
    s.text(b_x + b_w // 2, b_y + 52, "Board", BOX_T, C["ink"], bold=True)
    s.text(b_x + b_w // 2, b_y + 52 + LINE_H, "kanban.db", BOX, C["ink"])
    gap_cx = (fx0 + fw + b_x) // 2
    s.arrow(fx0 + fw + 4, pick_cy, b_x - 6, b_y + 95)
    s.text(gap_cx, (pick_cy + b_y + 95) // 2 - 26, "reads", SMALL, C["muted"])
    s.arrow(fx0 + fw + 4, upd_cy, b_x - 6, b_y + 140)
    s.text(gap_cx, (upd_cy + b_y + 140) // 2 - 26, "updates", SMALL, C["muted"])

    # ---- CHECK (like Muse's check, no Judge) ----
    y = y + 50
    s.down_arrow(fx, y - 50, y)
    jx, jw = fx - 1000, 2000
    check_y = y
    check_h = 240
    s.rect(jx, check_y, jw, check_h, C["box"], C["border"], 2)
    jcx = jx + jw // 2
    s.text(jcx, check_y + 52,
           "CHECK — Is there a next unblocked card?",
           BOX_T, C["ink"], bold=True)
    for i, ln in enumerate([
        "The supervisor looks for the next card each hour. No Judge model.",
        "If yes → next hour, the supervisor runs again (loop back).",
        "If no → the goal is done (or blocked) — the loop pauses until there is work.",
    ]):
        s.text(jcx, check_y + 52 + (i + 1) * 46, ln, BOX, C["ink"])
    check_cy = check_y + check_h // 2
    y = check_y + check_h

    # ---- LOOP BACK (right side): next hour → supervisor runs again ----
    loop_rx = 2700
    s.line(jx + jw, check_cy, loop_rx, check_cy)
    s.line(loop_rx, check_cy, loop_rx, sup_start_cy)
    s.arrow(loop_rx, sup_start_cy, fx0 + fw + 6, sup_start_cy)
    s.text((fx0 + fw + loop_rx) // 2, sup_start_cy - 22,
           "next hour — supervisor runs again", SMALL, C["muted"])

    # Files — where each piece lives (dev-1)
    y = y + 50
    NW = 2000
    NH = 48 + 44 + 4 * 40 + 16
    note_box(s, (W - NW) // 2, y, NW, NH,
             "Files — where each piece lives (dev-1)",
             ["AGENTS.md — /home/engineer/.openclaw/workspaces/<agent>/AGENTS.md (instruction + GOAL section)",
              "Supervisor job — OpenClaw cron, in openclaw.sqlite cron_jobs (hourly, runs agentTurn)",
              "Board — /home/engineer/.hermes/kanban.db (Hermes kanban; Tony's board, --board default)",
              "Subagent — dispatched via agentTurn to software-engineer (or the owning agent)"])
    y += NH

    # Implementation plan — 6 steps
    y = y + 50
    NH2 = 48 + 44 + 6 * 40 + 16
    note_box(s, (W - NW) // 2, y, NW, NH2,
             "Implementation plan — 6 steps (spec only, do not build until Den says so)",
             ["1 · Add the goal instruction to AGENTS.md (the system prompt).",
              "2 · Agent writes the goal into the GOAL section of AGENTS.md (durable).",
              "3 · Create the hourly supervisor OpenClaw job (cron, agentTurn).",
              "4 · Supervisor reads GOAL + board, picks next UNBLOCKED card, dispatches subagent.",
              "5 · Subagent builds the card, updates the board (kanban).",
              "6 · Verify: supervisor runs hourly, picks cards, board moves. No Judge, no goal tool."])
    y += NH2

    y = s.legend(y, [
        "Solid arrow = flow  ·  loop on the right = next hour, back to the supervisor job",
        "Same shape as the Hermes and Muse diagrams: goal → work cycle → check → loop back",
        "Plain boxes, black on white, as in Den's sketch",
    ])
    s._h = y
    return s.build(out_path)


if __name__ == "__main__":
    d = os.path.dirname(os.path.abspath(__file__))
    hermes_diagram(os.path.join(d, "hermes-goal-mechanism.svg"))
    muse_diagram(os.path.join(d, "muse-goal-mechanism.svg"))
    openclaw_muse_diagram(os.path.join(d, "openclaw-muse-design.svg"))
