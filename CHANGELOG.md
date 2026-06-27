# Changelog

All notable changes to reflect are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions aim for
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- README "vs. Claude Code's built-in memory" section: a head-to-head comparison table and an honest
  summary of the trade-offs (control/scale vs. maintenance; retrieval recall hinges on `description`
  quality).
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
- README restructured around a hero demo: tagline → animated loop → quickstart → how it works →
  anatomy of a memory → three-command table → reference. A table of contents, a narrative "How it
  works", a "What's inside" catalog, Philosophy, and mobile-robust layout diagrams.
- Animated demo GIF showing the full loop end to end (`/reflect` distills → `/reflect-curate`
  promotes varied realistic candidates → a later session's retrieval injection), reproducible via
  `assets/make-cast.py` + `agg` (asciicast → GIF).

## [0.1.0] — initial

### Added
- `/reflect` distiller and `/reflect-curate` curator skills (propose-and-approve loop).
- `hooks/retrieve.py` pull-based UserPromptSubmit retrieval over a self-owned store.
- `install.sh` / `uninstall.sh` (idempotent, engine/data split), `bin/run-nightly.sh` cron runner,
  `config.example.json`, README, and architecture docs.
