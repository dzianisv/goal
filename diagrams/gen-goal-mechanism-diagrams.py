#!/usr/bin/env python3
"""Goal mechanism diagrams — Hermes and Muse, in DEN'S SKETCH style.
Den rejected both earlier styles (big wide colored nodes; sequence
diagrams). His sketch (workspace/user/media_library/image/image-2.png)
is the reference: thin rounded boxes, plain black-on-white, small boxes,
a vertical message flow, a Tools box on the side with an arrow, and the
open question at the bottom answered: what injects the goal back, and when.

Facts (verified from code, 2026-11-15):
- Inference: the MAIN session infers the goal. The agent itself, in the
  same turn as the user message, declares it with
  goal(action="create", objective, acceptance_criteria). No background
  API call infers the goal. The only auxiliary model call is judge_goal,
  which only checks whether the goal is DONE.
- Injection (feeding the goal back): (1) heartbeat tick —
  next_continuation_prompt feeds the goal back as a user-role message;
  (2) idle-wake — the barrier-wake chore re-pokes an active goal with
  no turn for idle_wake_seconds (default 900s = 15 min). Both re-assert
  the EXISTING goal; neither infers a new one.
- Hermes source: /home/engineer/.hermes/hermes-agent/
  tools/goal_tool.py, hermes_cli/goals.py, agent/prompt_builder.py:240.
- Muse: the goal is set AUTOMATICALLY — Muse infers it from the
  project/conversation and declares it itself (docs/goals.md, system
  prompt, goal-mechanism-spec.md lines 9/50). No set-goal command from
  Den; the hourly supervisor re-asserts it each run. From the design
  description + Muse's goal docs, NOT from internals.

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


# ---- Hermes ----

def hermes_diagram(out_path):
    s = Svg()
    y = s.header(
        "How the goal works in Hermes",
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

    # Message flow, centred under Session 1 (centre x = cx - 600)
    fx = cx - 600  # flow centre
    fw = 640
    fx0 = fx - fw // 2
    gap = 34
    flow_y = y
    s.box(fx0, y, fw, 84, ["System message"])
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    s.box(fx0, y, fw, 84, ["User message"])
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    s.box(fx0, y, fw, 84, ["AI message"])
    y += 84
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Tool call — the inference, bold border
    tool_y = y
    s.box(fx0, tool_y, fw, 150,
          ["Tool call: goal",
           "{ create, objective,",
           "acceptance_criteria }"],
          bold_border=True, fill=C["hl_fill"])
    y = tool_y + 150

    # Tools box on the left, arrow from System message (as in the sketch)
    tools_x, tools_y, tools_w, tools_h = 60, flow_y + 10, 400, 250
    s.rect(tools_x, tools_y, tools_w, tools_h, C["box"], C["border"], 2)
    s.text(tools_x + tools_w // 2, tools_y + 52, "Tools:", BOX_T, C["ink"], bold=True)
    for i, t in enumerate(["goal", "read", "write"]):
        s.text(tools_x + tools_w // 2, tools_y + 52 + (i + 1) * LINE_H, t, BOX, C["ink"])
    # arrow: System message bottom edge -> Tools right edge (diagonal, as in sketch)
    s.arrow(fx - 180, flow_y + 84, tools_x + tools_w + 5, tools_y + 130)

    # Inference note, right of the tool-call box
    inf_x = fx0 + fw + 80
    inf_w = 1080
    s.rect(inf_x, tool_y - 10, inf_w, 200, C["hl_fill"], C["border"], 2)
    s.text(inf_x + 30, tool_y + 34, "★ AUTO-INFERRED — in the main session", BOX_T,
           C["ink"], bold=True, anchor="start")
    for i, ln in enumerate([
        "The agent itself, in the same turn as the user message,",
        "infers the goal and declares it with this call.",
        "No background API call infers the goal.",
    ]):
        s.text(inf_x + 30, tool_y + 34 + (i + 1) * 40, ln, SMALL, C["ink"],
               anchor="start")

    # Judge box, right of the AI message box
    ai_y = tool_y - gap - 84
    j_x = fx0 + fw + 80
    s.rect(j_x, ai_y - 10, inf_w, 104, C["box"], C["border"], 2)
    s.text(j_x + 30, ai_y + 32, "Judge (auxiliary model) — checks DONE only", BOX_T,
           C["ink"], bold=True, anchor="start")
    s.text(j_x + 30, ai_y + 32 + 42,
           "judge_goal asks only 'is the goal DONE?' — it never infers the goal.",
           SMALL, C["ink"], anchor="start")
    s.line(fx0 + fw + 4, ai_y + 42, j_x - 6, ai_y + 42, sw=2, dashed=True)

    # "..." then the injection box — answers the sketch's bottom question
    y = y + 40
    s.text(fx, y + 30, "…", 44, C["muted"])
    y += 62
    inj_x = cx - 1000
    inj_w = 2000
    inj_y = y
    s.rect(inj_x, inj_y, inj_w, 260, C["box"], C["border"], 2)
    s.text(cx, inj_y + 52,
           "What injects the goal back into the session?", BOX_T, C["ink"], bold=True)
    for i, ln in enumerate([
        "1 · Heartbeat tick — next_continuation_prompt feeds the goal back as a user-role message.",
        "2 · Idle-wake — the barrier-wake chore re-pokes an active goal after 15 min idle (idle_wake_seconds = 900).",
    ]):
        s.text(cx, inj_y + 52 + (i + 1) * 46, ln, BOX, C["ink"])
    s.text(cx, inj_y + 52 + 3 * 46 + 12,
           "Both re-assert the EXISTING goal. Never inferred in the background.",
           BOX, C["ink"], bold=True)
    y = inj_y + 260

    # Feedback arrow: injection box -> back up into the User message box
    user_y = tool_y - 2 * (gap + 84)  # top of User message box
    user_cy = user_y + 42
    rx = inj_x + inj_w - 60  # right side vertical
    s.line(rx, inj_y, rx, user_cy)
    s.arrow(rx, user_cy, fx0 + fw + 6, user_cy)
    s.text(rx - 260, inj_y - 16, "goal fed back in", SMALL, C["muted"],
           anchor="middle")

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
        "Solid arrow = call / flow  ·  dashed line = the judge, called after a turn and at complete",
        "Bold box = the auto-inferred goal  ·  plain boxes, black on white, as in Den's sketch",
    ])
    s._h = y
    return s.build(out_path)


# ---- Muse ----

def muse_diagram(out_path):
    s = Svg()
    y = s.header(
        "How the goal works in Muse",
        "From the design description + Muse's goal docs — NOT from Muse internals · do not read more into it")
    cx = W // 2
    fx = cx - 300          # flow centre (board box sits on the right)
    fw = 1200
    fx0 = fx - fw // 2
    gap = 34

    # Step 1 — Muse sets the goal AUTOMATICALLY (auto-inference, same as Hermes)
    s.box(fx0, y, fw, 150,
          ["★ 1 · Muse sets the goal AUTOMATICALLY",
           "infers it from the project / conversation and declares it itself",
           "no set-goal command from Den"],
          bold_border=True, fill=C["hl_fill"])
    y += 150
    s.down_arrow(fx, y, y + gap)
    y += gap
    # Supervisor — re-asserts the auto-inferred goal
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

    # Board box on the right (like Tools in the sketch)
    b_x, b_w = fx0 + fw + 220, 640
    b_y = sup_y + 40
    s.rect(b_x, b_y, b_w, 220, C["box"], C["border"], 2)
    s.text(b_x + b_w // 2, b_y + 52, "Board", BOX_T, C["ink"], bold=True)
    for i, ln in enumerate(["the cards", "goal: declared by Muse"]):
        s.text(b_x + b_w // 2, b_y + 52 + (i + 1) * LINE_H, ln, BOX, C["ink"])
    # arrows: supervisor reads, subagent updates (labels above the lines, in the gap)
    gap_cx = (fx0 + fw + b_x) // 2
    s.arrow(fx0 + fw + 4, pick_y + 48, b_x - 6, b_y + 110)
    s.text(gap_cx, (pick_y + 48 + b_y + 110) // 2 - 26, "reads", SMALL, C["muted"])
    s.arrow(fx0 + fw + 4, upd_y + 48, b_x - 6, b_y + 170)
    s.text(gap_cx, (upd_y + 48 + b_y + 170) // 2 - 26, "updates", SMALL, C["muted"])

    # Loop-back: next hour, supervisor runs again (left side)
    loop_x = 120
    s.line(fx, y, fx, y + 46)
    s.line(fx, y + 46, loop_x, y + 46)
    s.line(loop_x, y + 46, loop_x, sup_y + 70)
    s.arrow(loop_x, sup_y + 70, fx0 - 6, sup_y + 70)
    s.text(loop_x + 130, y + 46 - 14, "next hour — supervisor runs again",
           SMALL, C["muted"], anchor="start")

    # Bottom note
    y = y + 110
    NW = 2000
    NH = 48 + 44 + 3 * 40 + 16
    note_box(s, (W - NW) // 2, y, NW, NH,
             "The goal is set automatically — Den never issues a set-goal command",
             ["Muse infers the goal from the project / conversation and declares it itself.",
              "Den states what he wants in conversation — product owner, not goal-setter.",
              "No idle trigger — hourly schedule."])
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
