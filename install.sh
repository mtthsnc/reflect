#!/usr/bin/env bash
# reflect — installer. Wires this repo (the engine) into ~/.claude (your data).
# Idempotent: safe to re-run after `git pull`. No personal data is ever written
# into the repo; everything you generate lives under ~/.claude/reflection/.
#
# Usage:
#   ./install.sh              # skills + data dirs + retrieval hook
#   ./install.sh --cron       # also install the nightly cron job
#   ./install.sh --no-hook    # skip the UserPromptSubmit retrieval hook
#   ./install.sh --force      # overwrite an existing config.json with the template
set -euo pipefail

REPO="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"
CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
REFLECT_HOME="$CLAUDE_HOME/reflection"
SKILLS_DIR="$CLAUDE_HOME/skills"
SETTINGS="$CLAUDE_HOME/settings.json"

WANT_CRON=0; WANT_HOOK=1; FORCE=0
for arg in "$@"; do
  case "$arg" in
    --cron) WANT_CRON=1 ;;
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

# 3. state.json — cursor for the nightly engine.
STATE="$REFLECT_HOME/state.json"
if [ ! -f "$STATE" ]; then
  printf '%s\n' '{ "last_run_iso": null, "last_processed_mtime": 0, "processed_sessions": [], "runs": [] }' > "$STATE"
  say "initialized state.json"
fi

# 4. Skills — symlinked so `git pull` updates them live.
#    Back up any pre-existing real dir (or stale link) before linking.
for s in reflect reflect-review; do
  link="$SKILLS_DIR/$s"
  if [ -L "$link" ]; then
    rm -f "$link"
  elif [ -e "$link" ]; then
    mv "$link" "$link.pre-reflect.bak"
    say "backed up existing $s -> $s.pre-reflect.bak"
  fi
  ln -sfn "$REPO/skills/$s" "$link"
done
say "linked skills: reflect, reflect-review -> $SKILLS_DIR"

# 5. Retrieval hook -> settings.json (merge, idempotent).
chmod +x "$REPO/hooks/retrieve.py" "$REPO/bin/run-nightly.sh" 2>/dev/null || true
if [ "$WANT_HOOK" -eq 1 ]; then
  HOOK_CMD="$REPO/hooks/retrieve.py"
  python3 - "$SETTINGS" "$HOOK_CMD" <<'PY'
import json, os, sys
settings_path, hook_cmd = sys.argv[1], sys.argv[2]
try:
    with open(settings_path) as f: data = json.load(f)
except Exception:
    data = {}
hooks = data.setdefault("hooks", {})
ups = hooks.setdefault("UserPromptSubmit", [])
exists = any(
    h.get("command") == hook_cmd
    for group in ups if isinstance(group, dict)
    for h in group.get("hooks", []) if isinstance(h, dict)
)
if not exists:
    ups.append({"hooks": [{"type": "command", "command": hook_cmd}]})
os.makedirs(os.path.dirname(settings_path), exist_ok=True)
with open(settings_path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
print("  retrieval hook registered in", settings_path)
PY
else
  say "skipped retrieval hook (--no-hook)"
fi

# 6. Optional nightly cron.
if [ "$WANT_CRON" -eq 1 ]; then
  RUNNER="$REPO/bin/run-nightly.sh"
  LINE="30 2 * * * $RUNNER"
  current="$(crontab -l 2>/dev/null || true)"
  if printf '%s\n' "$current" | grep -Fq "$RUNNER"; then
    say "cron already present"
  else
    printf '%s\n%s\n' "$current" "$LINE" | grep -v '^$' | crontab -
    say "installed cron: $LINE"
  fi
fi

echo "reflect: done."
echo "  Run /reflect in a Claude Code session (or wait for cron), then /reflect-review to promote."
[ "$WANT_HOOK" -eq 1 ] && echo "  Restart Claude Code sessions so the retrieval hook takes effect."
exit 0
