#!/usr/bin/env bash
# reflect — uninstaller. Removes the wiring; keeps your data by default.
#
# Usage:
#   ./uninstall.sh           # remove skills symlinks, hook, cron (data kept)
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

# Hook out of settings.json.
if [ -f "$SETTINGS" ]; then
  python3 - "$SETTINGS" "$REPO/hooks/retrieve.py" <<'PY'
import json, sys
p, cmd = sys.argv[1], sys.argv[2]
try:
    with open(p) as f: data = json.load(f)
except Exception:
    sys.exit(0)
ups = data.get("hooks", {}).get("UserPromptSubmit", [])
for group in ups:
    if isinstance(group, dict):
        group["hooks"] = [h for h in group.get("hooks", []) if h.get("command") != cmd]
data.get("hooks", {})["UserPromptSubmit"] = [g for g in ups if g.get("hooks")]
if not data.get("hooks", {}).get("UserPromptSubmit"):
    data.get("hooks", {}).pop("UserPromptSubmit", None)
with open(p, "w") as f:
    json.dump(data, f, indent=2); f.write("\n")
print("  removed retrieval hook from settings.json")
PY
fi

# Cron.
if crontab -l 2>/dev/null | grep -Fq "$REPO/bin/run-nightly.sh"; then
  crontab -l 2>/dev/null | grep -Fv "$REPO/bin/run-nightly.sh" | crontab -
  say "removed cron entry"
fi

if [ "$PURGE" -eq 1 ]; then
  rm -rf "$REFLECT_HOME"
  say "PURGED $REFLECT_HOME (data deleted)"
else
  say "kept your data at $REFLECT_HOME"
fi
echo "reflect: uninstalled."
