#!/usr/bin/env bash
# reflect — uninstaller. Removes the wiring; keeps your data by default.
#
# Usage:
#   ./uninstall.sh           # remove skills symlinks, hooks (data kept)
#   ./uninstall.sh --purge   # ALSO delete ~/.claude/reflection (your memories!)
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
REFLECT_HOME="$CLAUDE_HOME/reflection"
SKILLS_DIR="$CLAUDE_HOME/skills"
SETTINGS="$CLAUDE_HOME/settings.json"
PURGE=0
[ "${1:-}" = "--purge" ] && PURGE=1

say() { printf '  %s\n' "$*"; }

# Skills (only remove if they point at this repo).
for s in reflect reflect-curate; do
  link="$SKILLS_DIR/$s"
  if [ -L "$link" ] && [ "$(readlink -f "$link")" = "$REPO/skills/$s" ]; then
    rm -f "$link"; say "removed skill link $s"
  fi
done

# Hooks out of settings.json (retrieval + session-end).
if [ -f "$SETTINGS" ]; then
  python3 - "$SETTINGS" \
    "UserPromptSubmit:$REPO/hooks/retrieve.py" \
    "SessionEnd:$REPO/hooks/on_session_end.py" <<'PY'
import json, sys
p = sys.argv[1]
pairs = [a.split(":", 1) for a in sys.argv[2:]]
try:
    with open(p) as f: data = json.load(f)
except Exception:
    sys.exit(0)
hooks = data.get("hooks", {})
removed = []
for event, cmd in pairs:
    groups = hooks.get(event, [])
    before = sum(len(g.get("hooks", [])) for g in groups if isinstance(g, dict))
    for group in groups:
        if isinstance(group, dict):
            group["hooks"] = [h for h in group.get("hooks", []) if h.get("command") != cmd]
    if sum(len(g.get("hooks", [])) for g in groups if isinstance(g, dict)) < before:
        removed.append(event)
    remaining = [g for g in groups if isinstance(g, dict) and g.get("hooks")]
    if remaining:
        hooks[event] = remaining
    else:
        hooks.pop(event, None)
with open(p, "w") as f:
    json.dump(data, f, indent=2); f.write("\n")
if removed:
    print("  removed hooks from settings.json:", ", ".join(removed))
PY
fi

# Stale cron from older installs (the SessionEnd hook replaced the nightly runner).
if crontab -l 2>/dev/null | grep -Fq "/bin/run-nightly.sh"; then
  { crontab -l 2>/dev/null | grep -Fv "/bin/run-nightly.sh" | crontab -; } || true
  say "removed stale nightly cron entry"
fi

if [ "$PURGE" -eq 1 ]; then
  rm -rf "$REFLECT_HOME"
  say "PURGED $REFLECT_HOME (data deleted)"
else
  say "kept your data at $REFLECT_HOME"
fi
echo "reflect: uninstalled."
