# Changelog

All notable changes to reflectr are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions aim for
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Conformance gate (`scripts/validate.sh`): shell syntax, shellcheck, ruff, JSON validity, and a
  skill frontmatter contract (requires `name` + a "Use when…" `description`, frontmatter ≤ 1024).
- Test suite (`tests/run.sh`): sandboxed install + retrieval-hook assertions (relevant hits,
  irrelevant misses, safe empty/malformed input).
- GitHub Actions CI running the gate and tests on push/PR.
- `.pre-commit-config.yaml` mirroring CI locally.
- Contributor docs: `AGENTS.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, issue/PR templates.

### Changed
- Skill descriptions rewritten as "Use when…" triggers (not workflow summaries) so agents read the
  skill body instead of the description. Added Overview and Common-mistakes sections to both skills.

## [0.1.0] — initial

### Added
- `/reflect` distiller and `/reflect-review` curator skills (propose-and-approve loop).
- `hooks/retrieve.py` pull-based UserPromptSubmit retrieval over a self-owned store.
- `install.sh` / `uninstall.sh` (idempotent, engine/data split), `bin/run-nightly.sh` cron runner,
  `config.example.json`, README, and architecture docs.
