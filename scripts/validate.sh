#!/usr/bin/env bash
# reflectr conformance gate. Runs locally, in pre-commit, and in CI.
# Hard gates: bash syntax, python compile, JSON validity, skill frontmatter contract.
# Advisory (run only if installed): shellcheck, ruff.
# Exit nonzero if any hard gate fails.
set -uo pipefail
cd "$(dirname "$(readlink -f "$0")")/.." || exit 2

fail=0
ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31m✗\033[0m %s\n' "$*"; fail=1; }
skip() { printf '  \033[33m–\033[0m %s\n' "$*"; }

echo "== shell syntax =="
while IFS= read -r f; do
  if bash -n "$f"; then ok "bash -n $f"; else bad "syntax error: $f"; fi
done < <(find . -name '*.sh' -not -path './.git/*' | sort)

echo "== shellcheck =="
if command -v shellcheck >/dev/null 2>&1; then
  while IFS= read -r f; do
    if shellcheck "$f"; then ok "shellcheck $f"; else bad "shellcheck: $f"; fi
  done < <(find . -name '*.sh' -not -path './.git/*' | sort)
else
  skip "shellcheck not installed"
fi

echo "== python =="
if python3 -m py_compile hooks/retrieve.py; then ok "py_compile hooks/retrieve.py"; else bad "py_compile failed"; fi
if command -v ruff >/dev/null 2>&1; then
  if ruff check hooks/; then ok "ruff hooks/"; else bad "ruff findings"; fi
else
  skip "ruff not installed"
fi

echo "== json =="
if python3 -c "import json,sys; json.load(open('config.example.json'))"; then
  ok "config.example.json is valid JSON"
else
  bad "config.example.json is invalid JSON"
fi

echo "== skill frontmatter contract =="
if python3 - <<'PY'; then ok "all skills valid"; else fail_py=1; fi
import glob, re, sys
bad = 0
for p in sorted(glob.glob("skills/*/SKILL.md")):
    raw = open(p, encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", raw, re.DOTALL)
    if not m:
        print(f"    missing/!malformed frontmatter: {p}"); bad = 1; continue
    front = m.group(1)
    if len(m.group(0)) > 1024:
        print(f"    frontmatter > 1024 chars: {p}"); bad = 1
    name = re.search(r"^name:\s*(.+)$", front, re.M)
    desc = re.search(r"^description:\s*(.+)$", front, re.M)
    if not name:
        print(f"    missing 'name': {p}"); bad = 1
    elif not re.match(r"^[A-Za-z0-9-]+$", name.group(1).strip()):
        print(f"    invalid name chars (letters/numbers/hyphens only): {p}"); bad = 1
    if not desc:
        print(f"    missing 'description': {p}"); bad = 1
    elif not desc.group(1).strip().lower().startswith("use when"):
        print(f"    description should start with 'Use when' (trigger, not summary): {p}"); bad = 1
sys.exit(bad)
PY
[ "${fail_py:-0}" -ne 0 ] && bad "skill frontmatter contract failed"

echo
if [ "$fail" -ne 0 ]; then
  echo "CONFORMANCE: FAIL"
  exit 1
fi
echo "CONFORMANCE: PASS"
