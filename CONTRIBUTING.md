# Contributing to reflectr

Thanks for helping! reflectr is small and self-verifying — if the gates are green, you're most of the
way there.

## Quick start

```bash
git clone https://github.com/mtthsnc/reflectr && cd reflectr

# linters (any one install method)
pip install ruff pre-commit
#   shellcheck: apt-get install shellcheck  — or grab a static release binary

pre-commit install                       # run the conformance gate on every commit
pre-commit install --hook-type pre-push  # run tests on every push

./scripts/validate.sh   # conformance gate
./tests/run.sh          # test suite (sandboxed, no network / no claude CLI needed)
```

## The bar

Two scripts define "correct"; CI runs both on every push and PR:

- **`scripts/validate.sh`** — shell syntax, shellcheck, `ruff`, JSON validity, and the skill
  frontmatter contract.
- **`tests/run.sh`** — installs into a throwaway `CLAUDE_HOME` and exercises the retrieval hook.

Green locally == green in CI. If you can't install a linter, CI will still run it — but please try.

## Conventions

- **No hardcoded paths.** Default to `~/.claude/...` or read from config. `grep -r /home/ .` over
  tracked files must be empty. See [AGENTS.md](AGENTS.md) for the full rules.
- **Skill descriptions start with "Use when…"** and describe *when to invoke*, not the workflow —
  this is enforced by the gate. Structure skill bodies as Overview → procedure → Common mistakes.
- **The retrieval hook stays stdlib-only and never blocks a prompt** (errors exit 0, no output).
- Commit messages: `feat:` / `fix:` / `docs:` / `test:` / `chore:`. Note user-facing changes in
  [CHANGELOG.md](CHANGELOG.md) under "Unreleased".

## Pull requests

1. Branch off `main`.
2. Make the change; keep `validate.sh` and `run.sh` green.
3. Open a PR using the template. Describe what changed and how you verified it.

By contributing you agree your work is licensed under the repo's [MIT License](LICENSE).
