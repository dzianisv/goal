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
- Judge (Hermes): judge_goal is an auxiliary model call, in the
  background. It runs AFTER a turn (evaluate_after_turn) and when the
  agent calls goal(action="complete") (the completion audit). It asks
  only "is the goal DONE?" — done / continue / blocked / wait. It runs
  per turn ONLY for USER-set goals. Agent (self-inferred) goals SKIP
  the per-turn judge — the heartbeat just continues them.
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

    # ---- JUDGE (after the turn, background) ----
    y = y + 50
    # dashed arrow from Turn ends down to the Judge
    s.arrow(fx, y - 50, fx, y, dashed=True)
    # Judge box — dashed border = background step
    jx, jw = cx - 1000, 2000
    judge_y = y
    s.dashed_rect(jx, judge_y, jw, 260, C["box"], C["border"], 2)
    jcx = jx + jw // 2
    s.text(jcx, judge_y + 52,
           "After the turn — Judge runs (auxiliary model, in the background)",
           BOX_T, C["ink"], bold=True)
    for i, ln in enumerate([
        "Judge asks only: is the goal DONE? → done / continue / blocked / wait",
        "Only for USER-set goals. Agent goals skip the judge — heartbeat just continues them.",
        "Goal done: agent calls goal(complete, evidence) → Judge audits → DONE → marked done.",
    ]):
        s.text(jcx, judge_y + 52 + (i + 1) * 46, ln, BOX, C["ink"])
    judge_cy = judge_y + 130
    y = judge_y + 260

    # ---- LOOP BACK (right side): next turn, goal fed back in ----
    loop_rx = 2700
    s.line(jx + jw, judge_cy, loop_rx, judge_cy)
    s.line(loop_rx, judge_cy, loop_rx, turn_cy)
    s.arrow(loop_rx, turn_cy, fx0 + fw + 6, turn_cy)
    s.text((fx0 + fw + loop_rx) // 2, turn_cy - 22, "next turn — goal fed back in",
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
        "Solid arrow = flow  ·  dashed arrow = the judge (background, after a turn)  ·  loop on the right = next turn, goal fed back in",
        "Inside a turn: AI message → tool calls → results, repeated till the agent stops calling tools",
        "Bold green box = the goal, inferred in the main session  ·  plain boxes, black on white, as in Den's sketch",
    ])
    s._h = y
    return s.build(out_path)


# ---- Muse: the honest mechanism ----

def muse_diagram(out_path):
    s = Svg()
    y = s.header(
        "How the goal works in Muse",
        "From the docs + system prompt — NOT from Muse internals (closed source) · do not read more into it")
    cx = W // 2
    fx = cx - 300          # flow centre (board box sits on the right)
    fw = 1200
    fx0 = fx - fw // 2
    gap = 34

    # Step 1 — the system-prompt instruction. THIS is the "automatic".
    s.box(fx0, y, fw, 150,
          ["★ 1 · System prompt: create a goal when the user",
           "shares an enduring aspiration — even without",
           "the word 'goal'. No set-goal command needed."],
          bold_border=True, fill=C["hl_fill"])
    y += 150
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Step 2 — durable goal
    s.box(fx0, y, fw, 140,
          ["Agent saves it as a DURABLE goal (Goals tab)",
           "a milestone, not a per-session goal"])
    y += 140
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Supervisor — re-asserts the goal
    s.box(fx0, y, fw, 140,
          ["Supervisor — hourly",
           "re-asserts that goal each run"])
    sup_y = y
    y += 140
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Pick the card
    s.box(fx0, y, fw, 96,
          ["Picks the next highest-priority UNBLOCKED card"])
    pick_y = y
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Subagent builds
    s.box(fx0, y, fw, 96, ["Subagent builds the picked card"])
    y += 96
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Subagent updates the board
    s.box(fx0, y, fw, 96, ["Subagent updates the board"])
    upd_y = y
    y += 96

    # Board box on the right
    b_x, b_w = fx0 + fw + 220, 640
    b_y = sup_y + 40
    s.rect(b_x, b_y, b_w, 180, C["box"], C["border"], 2)
    s.text(b_x + b_w // 2, b_y + 52, "Board", BOX_T, C["ink"], bold=True)
    for i, ln in enumerate(["the cards"]):
        s.text(b_x + b_w // 2, b_y + 52 + (i + 1) * LINE_H, ln, BOX, C["ink"])
    # arrows: supervisor reads, subagent updates (labels above the lines, in the gap)
    gap_cx = (fx0 + fw + b_x) // 2
    s.arrow(fx0 + fw + 4, pick_y + 48, b_x - 6, b_y + 95)
    s.text(gap_cx, (pick_y + 48 + b_y + 95) // 2 - 26, "reads", SMALL, C["muted"])
    s.arrow(fx0 + fw + 4, upd_y + 48, b_x - 6, b_y + 140)
    s.text(gap_cx, (upd_y + 48 + b_y + 140) // 2 - 26, "updates", SMALL, C["muted"])

    # Loop-back: next hour, supervisor runs again (left side)
    loop_x = 120
    s.line(fx, y, fx, y + 46)
    s.line(fx, y + 46, loop_x, y + 46)
    s.line(loop_x, y + 46, loop_x, sup_y + 70)
    s.arrow(loop_x, sup_y + 70, fx0 - 6, sup_y + 70)
    s.text(loop_x + 130, y + 46 - 14, "next hour — supervisor runs again",
           SMALL, C["muted"], anchor="start")

    # Bottom note — what Muse does NOT have
    y = y + 110
    NW = 2000
    NH = 48 + 44 + 4 * 40 + 16
    note_box(s, (W - NW) // 2, y, NW, NH,
             "What Muse does NOT have (unlike Hermes)",
             ["No per-session goal tool. No judge. No per-turn goal check.",
              "Muse's goals are durable milestones in the Goals tab, kept alive",
              "by the system-prompt instruction + the hourly supervisor job.",
              "Internals are closed — this is from the docs + system prompt, not source code."])
    y += NH

    y = s.legend(y, [
        "Solid arrow = flow  ·  loop on the left = every hour, back to the supervisor",
        "Plain boxes, black on white, as in Den's sketch",
    ])
    s._h = y
    return s.build(out_path)


if __name__ == "__main__":
    d = os.path.dirname(os.path.abspath(__file__))
    hermes_diagram(os.path.join(d, "hermes-goal-mechanism.svg"))
    muse_diagram(os.path.join(d, "muse-goal-mechanism.svg"))
