#!/usr/bin/env bash
# reflect test suite. Installs into a throwaway CLAUDE_HOME and exercises the
# retrieval hook against a fixture store. No network, no claude CLI needed.
# Exit nonzero on any failed assertion.
set -uo pipefail
REPO="$(cd "$(dirname "$(readlink -f "$0")")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail=0
ok()  { printf '  \033[32m✓\033[0m %s\n' "$*"; }
bad() { printf '  \033[31m✗\033[0m %s\n' "$*"; fail=1; }

echo "== install into sandbox =="
CLAUDE_HOME="$TMP/home" bash "$REPO/install.sh" >/dev/null 2>&1 || bad "install.sh exited nonzero"
H="$TMP/home"
for d in reflection/store/memories reflection/store/docs reflection/queue/memories reflection/digests reflection/logs skills; do
  [ -d "$H/$d" ] && ok "created $d" || bad "missing dir $d"
done
[ -L "$H/skills/reflect" ] && ok "reflect skill symlinked" || bad "reflect not symlinked"
[ -L "$H/skills/reflect-stage" ] && ok "reflect-stage symlinked" || bad "reflect-stage not symlinked"
[ -f "$H/reflection/config.json" ] && ok "config.json generated" || bad "config.json missing"
python3 -c "import json; json.load(open('$H/reflection/config.json'))" 2>/dev/null \
  && ok "config.json valid JSON" || bad "config.json invalid"
grep -q '~' "$H/reflection/config.json" && bad "config.json still has literal ~" || ok "config.json paths expanded"
grep -q UserPromptSubmit "$H/settings.json" && ok "retrieval hook registered" || bad "hook not registered"

echo "== idempotent re-install =="
CLAUDE_HOME="$H" bash "$REPO/install.sh" >/dev/null 2>&1 || bad "re-install exited nonzero"
n=$(python3 -c "import json; print(len(json.load(open('$H/settings.json'))['hooks']['UserPromptSubmit']))" 2>/dev/null)
[ "$n" = "1" ] && ok "no duplicate hook on re-run" || bad "hook duplicated (count=$n)"

echo "== retrieval hook =="
FH="$TMP/fake"
mkdir -p "$FH/.claude/reflection/store/memories" "$FH/.claude/reflection/store/docs"
python3 - "$FH" "$REPO" <<'PY'
import json, sys
fh, repo = sys.argv[1], sys.argv[2]
base = f"{fh}/.claude/reflection"
cfg = json.load(open(f"{repo}/config.example.json"))
cfg["targets"] = {"memories_dir": f"{base}/store/memories", "docs_dir": f"{base}/store/docs"}
json.dump(cfg, open(f"{base}/config.json", "w"))
open(f"{base}/store/memories/relevant.md", "w").write(
    "---\nname: relevant\ndescription: design tokens conformance gates frontend conventions\n"
    "metadata:\n  type: project\n---\nBody about design tokens and gates.\n")
open(f"{base}/store/memories/unrelated.md", "w").write(
    "---\nname: unrelated\ndescription: postgres nightly backup restore pg_dump\n"
    "metadata:\n  type: reference\n---\nBody about databases.\n")
PY

out="$(printf '{"prompt":"frontend conventions and conformance gates for our design tokens"}' | HOME="$FH" python3 "$REPO/hooks/retrieve.py")"
echo "$out" | grep -q "## relevant" && ok "surfaces relevant entry" || bad "missed relevant entry"
echo "$out" | grep -q "## unrelated" && bad "surfaced irrelevant entry" || ok "filtered irrelevant entry"

printf '{"prompt":""}' | HOME="$FH" python3 "$REPO/hooks/retrieve.py" >/dev/null 2>&1 \
  && ok "empty prompt exits 0" || bad "empty prompt failed"
printf 'not json at all' | HOME="$FH" python3 "$REPO/hooks/retrieve.py" >/dev/null 2>&1 \
  && ok "malformed stdin exits 0" || bad "malformed stdin failed"

# Hook must NEVER emit output when there is no match (would pollute every prompt).
miss="$(printf '{"prompt":"completely orthogonal kangaroo xylophone"}' | HOME="$FH" python3 "$REPO/hooks/retrieve.py")"
[ -z "$miss" ] && ok "no output when nothing matches" || bad "emitted output with no match"

echo "== session-aware dedup =="
DP='{"prompt":"frontend conventions and conformance gates for our design tokens","session_id":"sess1"}'
first="$(printf '%s' "$DP" | HOME="$FH" python3 "$REPO/hooks/retrieve.py")"
echo "$first" | grep -q "Body about design tokens" && ok "first prompt injects full body" || bad "first prompt missing full body"
second="$(printf '%s' "$DP" | HOME="$FH" python3 "$REPO/hooks/retrieve.py")"
echo "$second" | grep -q "already loaded earlier this session" && ok "repeat prompt emits pointer" || bad "repeat prompt missing pointer"
echo "$second" | grep -q "Body about design tokens" && bad "repeat prompt re-injected full body" || ok "repeat prompt suppresses full body"
# A different session must still get the full body (cache is per-session).
other="$(printf '{"prompt":"design tokens conformance gates","session_id":"sess2"}' | HOME="$FH" python3 "$REPO/hooks/retrieve.py")"
echo "$other" | grep -q "Body about design tokens" && ok "fresh session injects full body" || bad "fresh session missing full body"

echo "== graph edge expansion =="
GH="$TMP/ghome"
mkdir -p "$GH/.claude/reflection/store/memories"
GBASE="$GH/.claude/reflection"
python3 - "$GH" "$REPO" <<'PY'
import json, sys
gh, repo = sys.argv[1], sys.argv[2]
base = f"{gh}/.claude/reflection"
cfg = json.load(open(f"{repo}/config.example.json"))
cfg["targets"] = {"memories_dir": f"{base}/store/memories", "docs_dir": f"{base}/store/docs"}
json.dump(cfg, open(f"{base}/config.json", "w"))
open(f"{base}/store/memories/acme.md", "w").write(
    "---\nname: acme\ndescription: acme ai company profile\n---\n[[Bob]] works at [[Acme AI]].\n")
open(f"{base}/store/memories/bob.md", "w").write(
    "---\nname: bob\ndescription: engineer biography person\n---\n[[Bob]] is an engineer.\n")
PY
HOME="$GH" python3 "$REPO/hooks/wire.py" "$GBASE/store/memories/acme.md" "$GBASE/store/memories/bob.md"

q='{"prompt":"acme ai company"}'
on="$(printf '%s' "$q" | HOME="$GH" python3 "$REPO/hooks/retrieve.py")"
echo "$on" | grep -q "## bob" && ok "graph expansion surfaces linked neighbor" || bad "graph expansion missed neighbor"

python3 - "$GH" <<'PY'
import json, sys
base = f"{sys.argv[1]}/.claude/reflection"
cfg = json.load(open(f"{base}/config.json"))
cfg["graph"]["enabled"] = False
json.dump(cfg, open(f"{base}/config.json", "w"))
PY
off="$(printf '%s' "$q" | HOME="$GH" python3 "$REPO/hooks/retrieve.py")"
echo "$off" | grep -q "## bob" && bad "neighbor surfaced with graph disabled" || ok "ablation: no neighbor when graph off"

echo "== unit tests =="
( cd "$REPO" && python3 -m unittest discover -s tests -p 'test_*.py' >/dev/null 2>&1 ) \
  && ok "python unit tests pass" || bad "python unit tests failed"

echo "== session-end graphify catch-up is non-fatal =="
FCH="$TMP/fake-catchup"; mkdir -p "$FCH/.claude/reflection/store/memories"
echo '{"graph":{"graphify_enabled":true}}' > "$FCH/.claude/reflection/config.json"
( HOME="$FCH" PATH="$(dirname "$(command -v python3)"):/usr/bin:/bin" python3 -c "
import sys; sys.path.insert(0, '$REPO/hooks')
import graphify_sync
graphify_sync.graphify_catchup()
print('ok')
" ) | grep -q ok && ok "catch-up returns cleanly when graphify absent" || bad "catch-up raised without graphify"

echo
if [ "$fail" -ne 0 ]; then
  echo "TESTS: FAIL"
  exit 1
fi
echo "TESTS: PASS"
