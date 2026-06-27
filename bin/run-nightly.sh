#!/usr/bin/env bash
# reflect — nightly runner (invoked by cron). Runs the /reflect skill headless.
# Queue-only by design: stages candidates + writes a digest, never promotes to live.
# Portable: resolves the claude binary and paths at runtime, no hardcoded user.
set -uo pipefail

CLAUDE_HOME="${CLAUDE_HOME:-$HOME/.claude}"
REFLECT_HOME="$CLAUDE_HOME/reflection"
LOG_DIR="$REFLECT_HOME/logs"
DATE="$(date +%Y-%m-%d)"
RUN_LOG="$LOG_DIR/cron-$DATE.log"

# Find the claude CLI (PATH, then common install locations).
CLAUDE_BIN="$(command -v claude 2>/dev/null || true)"
for cand in "$HOME/.local/bin/claude" "$HOME/.claude/local/claude" "/usr/local/bin/claude"; do
  [ -z "$CLAUDE_BIN" ] && [ -x "$cand" ] && CLAUDE_BIN="$cand"
done

mkdir -p "$LOG_DIR"
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }

if [ -z "$CLAUDE_BIN" ]; then
  echo "[$(ts)] ERROR: claude CLI not found on PATH" >> "$RUN_LOG"
  exit 127
fi

echo "[$(ts)] nightly reflect starting ($CLAUDE_BIN)" >> "$RUN_LOG"
cd "$HOME" || exit 1
"$CLAUDE_BIN" -p "/reflect" \
  --permission-mode bypassPermissions \
  --add-dir "$CLAUDE_HOME" \
  >> "$RUN_LOG" 2>&1
STATUS=$?
echo "[$(ts)] nightly reflect finished (exit $STATUS)" >> "$RUN_LOG"
exit $STATUS
