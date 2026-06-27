# AGENTS.md

Guidance for coding agents (and humans) working **on** the reflect repo. For what the tool does and
how to install it, see [README.md](README.md); for the design, [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## What this repo is

reflect is the **engine** for a self-improving knowledge loop on Claude Code. It ships skills, a
retrieval hook, scripts, and a config template. It contains **no personal data** — everything a user
generates lives under `~/.claude/reflection/` and is gitignored. Never commit memories, digests,
queue contents, logs, or a generated `config.json`.

## Golden rules

1. **No hardcoded user/home/project paths.** Default to `~/.claude/...` (resolves per user) or read
   the value from config. The only safe literal anchors are `~/.claude/reflection/config.json` and
   `~/.claude/skills/`. A grep for `/home/` in tracked files should return nothing.
2. **The conformance gate is law.** `./scripts/validate.sh` must pass before any commit;
   `./tests/run.sh` before any push. CI runs both.
3. **Skill `description` = trigger, not summary.** Start every skill description with "Use when…" and
   describe *when to invoke*, never the workflow. A description that summarizes the steps makes agents
   follow the summary instead of reading the skill body. (The gate enforces the "Use when" prefix.)
4. **The retrieval hook must never block a prompt.** Any failure path in `hooks/retrieve.py` exits 0
   with no output. Keep it stdlib-only.

## Layout

```
skills/<name>/SKILL.md   skills (symlinked into ~/.claude/skills on install)
hooks/retrieve.py        UserPromptSubmit retrieval hook (stdlib only)
bin/run-nightly.sh       cron runner (resolves claude via command -v)
scripts/validate.sh      conformance gate (syntax, lint, JSON, skill contract)
tests/run.sh             sandbox install + retrieval assertions
config.example.json      config template (install expands ~ to $HOME)
install.sh uninstall.sh  idempotent wiring into ~/.claude
```

## Working here

- **Add/edit a skill:** create `skills/<name>/SKILL.md` with frontmatter `name` (letters/numbers/
  hyphens) + `description` ("Use when…", ≤ ~500 chars, frontmatter ≤ 1024). Structure the body as
  Overview → procedure → Common mistakes → Guardrails. Run `./scripts/validate.sh`.
- **Change retrieval:** edit `hooks/retrieve.py`, then `./tests/run.sh` (it asserts relevant hits,
  irrelevant misses, and safe handling of empty/malformed input). Keep it dependency-free.
- **Change install/cron:** keep `install.sh` idempotent and re-run-safe; `./tests/run.sh` covers it.

## Local setup

```bash
pip install ruff pre-commit        # or use the standalone binaries
# shellcheck: apt-get install shellcheck (or a static release binary)
pre-commit install && pre-commit install --hook-type pre-push
./scripts/validate.sh && ./tests/run.sh
```

## Commits & PRs

- Conventional-ish prefixes: `feat:`, `fix:`, `docs:`, `test:`, `chore:`.
- Update [CHANGELOG.md](CHANGELOG.md) under "Unreleased" for user-facing changes.
- Open PRs against `main`; CI must be green.
