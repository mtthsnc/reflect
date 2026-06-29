#!/usr/bin/env python3
"""
reflect — SessionEnd hook.

Fires the /reflect-stage distiller at real session boundaries (/clear, exit/logout,
end of -p input). Event-driven, so unlike the nightly cron it does not depend on
the machine being awake at a fixed hour — it runs the moment a session ends,
while the machine is provably up.

Design rules (mirror hooks/retrieve.py):
  - NEVER block or delay exit. SessionEnd output is ignored anyway; any error -> exit 0.
  - Dependency-free (stdlib only). No jq.
  - Recursion-safe: the spawned reflect run is itself a session whose SessionEnd
    re-fires this hook. The REFLECT_RUNNING sentinel breaks that loop.
  - Cheap by default: skip trivial sessions (size gate), run on a small model.
"""
import json
import os
import shutil
import subprocess
import sys

# 1. Recursion guard: a reflect run sets this in its env; its own SessionEnd
#    (reason "prompt_input_exit") must be a no-op, or we loop forever.
if os.environ.get("REFLECT_RUNNING"):
    sys.exit(0)

# 2. Parse the hook payload (Claude Code passes JSON on stdin). Any failure -> nothing.
try:
    event = json.load(sys.stdin)
except Exception:
    sys.exit(0)

# 3. Only distill on a real session boundary. /clear and the various exits qualify;
#    a suspend-for-resume does not (nothing actually ended).
REFLECT_REASONS = {"clear", "logout", "prompt_input_exit", "other"}
if event.get("reason") not in REFLECT_REASONS:
    sys.exit(0)

graphify_sync = os.path.join(os.path.dirname(os.path.abspath(__file__)), "graphify_sync.py")
try:
    subprocess.Popen(["python3", graphify_sync],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)
except Exception:
    pass

HOME = os.path.expanduser("~")
CLAUDE_HOME = os.environ.get("CLAUDE_HOME") or os.path.join(HOME, ".claude")
REFLECT_HOME = os.path.join(CLAUDE_HOME, "reflection")

# 4. Size gate: don't boot a model for a throwaway session. Threshold from config,
#    same knob the engine uses when scanning.
min_bytes = 4000
try:
    with open(os.path.join(REFLECT_HOME, "config.json")) as f:
        min_bytes = int(json.load(f).get("scan", {}).get("min_session_bytes", 4000))
except Exception:
    pass
transcript = event.get("transcript_path", "")
try:
    if os.path.getsize(transcript) < min_bytes:
        sys.exit(0)
except OSError:
    sys.exit(0)

# 5. Resolve the claude CLI (PATH, then common install locations).
claude = shutil.which("claude")
if not claude:
    for cand in (os.path.join(HOME, ".local/bin/claude"),
                 os.path.join(HOME, ".claude/local/claude"),
                 "/usr/local/bin/claude"):
        if os.access(cand, os.X_OK):
            claude = cand
            break
if not claude:
    sys.exit(0)

model = os.environ.get("REFLECT_MODEL") or "claude-haiku-4-5"
cmd = [claude, "-p", "/reflect-stage",
       "--model", model,
       "--permission-mode", "bypassPermissions",
       "--add-dir", CLAUDE_HOME]

# 6. Dry-run escape hatch for tests: print the command, don't launch.
if os.environ.get("REFLECT_DRY_RUN"):
    print(" ".join(cmd))
    sys.exit(0)

# 7. Launch detached so it outlives this hook and the ending session.
try:
    os.makedirs(os.path.join(REFLECT_HOME, "logs"), exist_ok=True)
    logf = open(os.path.join(REFLECT_HOME, "logs", "session-end.log"), "a")
    subprocess.Popen(
        cmd,
        cwd=HOME,
        env={**os.environ, "REFLECT_RUNNING": "1"},
        stdin=subprocess.DEVNULL,
        stdout=logf,
        stderr=logf,
        start_new_session=True,
    )
except Exception:
    pass
sys.exit(0)
