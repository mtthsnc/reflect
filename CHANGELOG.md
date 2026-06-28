# Changelog

All notable changes to reflect are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions aim for
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `SessionEnd` hook (`hooks/on_session_end.py`): event-driven trigger that runs `/reflect` at real
  session boundaries (`/clear`, logout, end of `-p` input), so distillation is tied to when sessions
  actually end rather than a fixed clock schedule. Recursion-safe via a `REFLECT_RUNNING` sentinel,
  size-gated (skips trivial sessions), runs detached on a small model (`REFLECT_MODEL`, default
  `claude-haiku-4-5`). Wired idempotently by `install.sh`.
- README "vs. Claude Code's built-in memory" section: an accurate head-to-head with Claude Code's
  auto memory (which is itself bounded — `MEMORY.md` index + on-demand topic files), framing
  reflect's real differences as the approval gate, deterministic per-prompt injection, transcript
  distillation, cross-project scope, and skills.
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

### Removed
- Nightly cron and `bin/run-nightly.sh`, and the `--cron` install flag. The `SessionEnd` hook
  replaces them — distillation now runs when a session ends rather than at a fixed hour, which also
  fixes the failure mode where the scheduled run never fired on a sleeping/closed machine.
  `install.sh` removes any stale reflect cron entry on upgrade.

## [0.1.0] — initial

### Added
- `/reflect` distiller and `/reflect-curate` curator skills (propose-and-approve loop).
- `hooks/retrieve.py` pull-based UserPromptSubmit retrieval over a self-owned store.
- `install.sh` / `uninstall.sh` (idempotent, engine/data split),
  `hooks/on_session_end.py` SessionEnd trigger, `config.example.json`, README, and architecture docs.
