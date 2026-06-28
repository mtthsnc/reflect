#!/usr/bin/env bash
# reflect — installer. Wires this repo (the engine) into ~/.claude (your data).
# Idempotent: safe to re-run after `git pull`. No personal data is ever written
# into the repo; everything you generate lives under ~/.claude/reflection/.
#
# Usage:
#   ./install.sh              # skills + data dirs + retrieval & session-end hooks
#   ./install.sh --no-hook    # skip the hooks (retrieval + session-end)
#   ./install.sh --force      # overwrite an existing config.json with the template
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
REFLECT_HOME="$CLAUDE_HOME/reflection"
SKILLS_DIR="$CLAUDE_HOME/skills"
SETTINGS="$CLAUDE_HOME/settings.json"

WANT_HOOK=1; FORCE=0
for arg in "$@"; do
  case "$arg" in
    --no-hook) WANT_HOOK=0 ;;
    --force) FORCE=1 ;;
    -h|--help) grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown arg: $arg" >&2; exit 2 ;;
  esac
done

say() { printf '  %s\n' "$*"; }
echo "reflect: installing from $REPO"
echo "         into $CLAUDE_HOME"

# 1. Data dirs (out of repo, gitignored by living here).
mkdir -p \
  "$REFLECT_HOME"/queue/{memories,skills,docs} \
  "$REFLECT_HOME"/store/{memories,docs} \
  "$REFLECT_HOME"/digests \
  "$REFLECT_HOME"/logs \
  "$SKILLS_DIR"
say "data dirs ready under $REFLECT_HOME"

# 2. config.json — generated from template with ~ expanded to your $HOME.
CONFIG="$REFLECT_HOME/config.json"
if [ -f "$CONFIG" ] && [ "$FORCE" -eq 0 ]; then
  say "config.json exists — kept (use --force to replace)"
else
  sed "s|~|$HOME|g" "$REPO/config.example.json" > "$CONFIG"
  say "wrote $CONFIG"
fi

# 3. state.json — cursor for the engine.
STATE="$REFLECT_HOME/state.json"
if [ ! -f "$STATE" ]; then
  printf '%s\n' '{ "last_run_iso": null, "last_processed_mtime": 0, "processed_sessions": [], "runs": [] }' > "$STATE"
  say "initialized state.json"
fi

# 4. Skills — symlinked so `git pull` updates them live.
#    Back up any pre-existing real dir (or stale link) before linking.
for s in reflect reflect-curate; do
  link="$SKILLS_DIR/$s"
  if [ -L "$link" ]; then
    rm -f "$link"
  elif [ -e "$link" ]; then
    mv "$link" "$link.pre-reflect.bak"
    say "backed up existing $s -> $s.pre-reflect.bak"
  fi
  ln -sfn "$REPO/skills/$s" "$link"
done
say "linked skills: reflect, reflect-curate -> $SKILLS_DIR"

# 5. Hooks -> settings.json (merge, idempotent).
#    UserPromptSubmit retrieval (pull) + SessionEnd reflect trigger (push on /clear & exit).
chmod +x "$REPO/hooks/retrieve.py" "$REPO/hooks/on_session_end.py" 2>/dev/null || true
if [ "$WANT_HOOK" -eq 1 ]; then
  python3 - "$SETTINGS" \
    "UserPromptSubmit:$REPO/hooks/retrieve.py" \
    "SessionEnd:$REPO/hooks/on_session_end.py" <<'PY'
import json, os, sys
settings_path = sys.argv[1]
pairs = [a.split(":", 1) for a in sys.argv[2:]]
try:
    with open(settings_path) as f: data = json.load(f)
except Exception:
    data = {}
hooks = data.setdefault("hooks", {})
for event, cmd in pairs:
    groups = hooks.setdefault(event, [])
    exists = any(
        h.get("command") == cmd
        for group in groups if isinstance(group, dict)
        for h in group.get("hooks", []) if isinstance(h, dict)
    )
    if exists:
        print(f"  {event} hook already present")
        continue
    entry = {"type": "command", "command": cmd}
    if event == "SessionEnd":
        entry["async"] = True  # detached; never delays exit
    groups.append({"hooks": [entry]})
    print(f"  registered {event} hook: {cmd}")
os.makedirs(os.path.dirname(settings_path), exist_ok=True)
with open(settings_path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY
else
  say "skipped hooks (--no-hook)"
fi

# 6. Migration: older installs wired a 02:30 cron runner. The SessionEnd hook
#    replaces it — drop any stale entry so it doesn't fire a now-removed script.
if crontab -l 2>/dev/null | grep -Fq "/bin/run-nightly.sh"; then
  { crontab -l 2>/dev/null | grep -Fv "/bin/run-nightly.sh" | crontab -; } || true
  say "removed stale nightly cron (replaced by the SessionEnd hook)"
fi

echo "reflect: done."
echo "  Reflect runs when a session ends (/clear or exit), or run /reflect on demand. Then /reflect-curate to promote."
[ "$WANT_HOOK" -eq 1 ] && echo "  Restart Claude Code sessions so the hooks take effect."
exit 0
