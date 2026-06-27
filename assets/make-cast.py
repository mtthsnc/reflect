#!/usr/bin/env python3
"""
Generate assets/demo.cast — an asciicast v2 recording of the full reflect
loop: /reflect distills, /reflect-curate promotes, and a later session shows the
retrieval hook injecting the approved memory automatically.

Illustrative, scripted demo (the real flow is interactive with Claude), but every
line mirrors the actual skill + hook output. Regenerate the gif:

    python3 assets/make-cast.py
    agg --theme monokai --font-size 15 --font-family "DejaVu Sans Mono" \
        assets/demo.cast assets/demo.gif
"""
import json
import os

WIDTH, HEIGHT = 90, 26

R = "\033[0m"; DIM = "\033[2m"; B = "\033[1m"
GRN = "\033[32m"; RED = "\033[31m"; CYN = "\033[36m"; YLW = "\033[33m"; MAG = "\033[35m"

events = []
t = 0.4


def out(s, dt=0.0):
    global t
    t += dt
    events.append([round(t, 3), "o", s])


def line(s="", dt=0.22):
    out(s + "\r\n", dt)


def typed(prefix, text, dt=0.045, after=0.6):
    out(prefix)
    for ch in text:
        out(ch, dt)
    out("\r\n", after)


def rule(label):
    bar = "─" * 14
    line(f"{DIM}{bar}  {label}  {bar}{R}", 0.5)


# ── Scene 1 — /reflect distills the day's sessions ──────────────────────────
line(f"{DIM}$ claude{R}", 0.6)
typed(f"{CYN}>{R} ", "/reflect", dt=0.07, after=0.7)
line("", 0.2)
line(f"{DIM}Reading 4 new sessions since the last run…{R}", 1.0)
line(f"  {GRN}▸{R} staged {B}3 memories{R} + {B}1 doc{R}  {DIM}· digest written{R}", 0.6)
line(f"  {DIM}Nothing is live yet — run /reflect-curate to approve.{R}", 1.2)
line("", 0.3)

# ── Scene 2 — /reflect-curate: curate the queue ─────────────────────────────
typed(f"{CYN}>{R} ", "/reflect-curate", dt=0.06, after=0.7)
line("", 0.2)
line(f"{B}▸ Reflection queue{R}  {DIM}(3 memories · 1 doc){R}", 0.6)
line("", 0.2)
line(f"{B}Memories{R}", 0.3)
line(f"  • {CYN}project-frontend-context-protocol{R}  {DIM}[project]{R}", 0.35)
line(f"      {DIM}conventions-as-code + conformance gates, self-verifying{R}", 0.35)
line(f"  • {CYN}feedback-prefer-tilde-paths{R}        {DIM}[feedback]{R}", 0.35)
line(f"      {DIM}default install paths to ~/.claude, never absolute{R}", 0.35)
line(f"  • {CYN}ref-agg-gif{R}                        {DIM}[reference]{R}", 0.35)
line(f"      {DIM}render an asciicast to GIF with agg{R}", 0.35)
line(f"{B}Docs{R}", 0.3)
line(f"  • {CYN}frontend-context-protocol{R}          {DIM}BCP→frontend mapping{R}", 0.5)
line("", 0.3)
line(f"{B}Approve all, reject all, or pick per-item?{R}", 0.6)
typed(f"{CYN}>{R} ", "keep the project + feedback memories and the doc; drop the ref",
      dt=0.035, after=0.8)
line("", 0.2)
line(f"{DIM}Promoting…{R}", 0.8)
line(f"  {GRN}✓{R} project-frontend-context-protocol  {DIM}→ store/memories/{R}", 0.4)
line(f"  {GRN}✓{R} feedback-prefer-tilde-paths        {DIM}→ store/memories/{R}", 0.4)
line(f"  {GRN}✓{R} frontend-context-protocol          {DIM}→ store/docs/{R}", 0.4)
line(f"  {RED}✗{R} {DIM}rejected: ref-agg-gif{R}", 0.4)
line(f"  {GRN}✓{R} INDEX.md regenerated  {DIM}· queue cleared{R}", 0.6)
line("", 0.2)
line(f"{B}Done.{R} 3 promoted, 1 rejected.", 1.4)
line("", 0.3)

# ── Scene 3 — a week later: retrieval pays off, untouched by you ─────────────
rule("a week later · a new session")
typed(f"{CYN}>{R} ", "set up design tokens and eslint rules for the component library",
      dt=0.03, after=0.7)
line("", 0.2)
line(f"  {MAG}«reflect»{R} {DIM}injected 1 memory:{R}", 0.7)
line(f"{MAG}<reflect-memory>{R}", 0.3)
line(f"{DIM}## project-frontend-context-protocol{R}", 0.3)
line(f"{DIM}Frontend analog of a Brand Context Protocol: design tokens +{R}", 0.25)
line(f"{DIM}component API conventions + a11y/code-style rules + ADRs as{R}", 0.25)
line(f"{DIM}machine-readable files, with conformance gates that refine it.{R}", 0.25)
line(f"{MAG}</reflect-memory>{R}", 0.7)
line("", 0.3)
line("Great — let's start from your Frontend Context Protocol. First, the", 0.3)
line("design-token source of truth, then the lint rules that enforce it…", 2.0)

header = {"version": 2, "width": WIDTH, "height": HEIGHT,
         "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"}}
dst = os.path.join(os.path.dirname(__file__), "demo.cast")
with open(dst, "w", encoding="utf-8") as f:
    f.write(json.dumps(header) + "\n")
    for e in events:
        f.write(json.dumps(e, ensure_ascii=False) + "\n")
print(f"wrote {dst} ({len(events)} events, {events[-1][0]}s)")
