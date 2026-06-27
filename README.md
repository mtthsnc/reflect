# reflectr

[![CI](https://github.com/mtthsnc/reflectr/actions/workflows/ci.yml/badge.svg)](https://github.com/mtthsnc/reflectr/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A self-improving knowledge loop for [Claude Code](https://claude.com/claude-code). Every night it
reads your session transcripts, distills them into **proposed** memories, skills, and docs, and
stages them for review. You approve the good ones; they land in a personal knowledge store that
future sessions **pull from automatically** via a retrieval hook.

The loop, end to end:

```
sessions ──/reflect──▶ queue ──/reflect-review──▶ store ──retrieval hook──▶ future sessions
 (.jsonl)   (nightly,    (you      (promote)      (memories  (top-k injected   (context, no
            queue-only)  approve)                  + docs)    per prompt)       supervision)
```

## Why it scales

The store is **pulled, not preloaded**. Older "load all memories every session" designs grow an
always-on context tax and need constant pruning. Here, a `UserPromptSubmit` hook scores each prompt
against every entry's `description` and injects only the **top-k** matches. The store can grow to
thousands of entries while per-session cost stays flat — and there's no index to babysit.

## Engine vs. data

This repo is the **engine** — skills, scripts, the hook, config template. It contains **no personal
data**. Everything you generate (memories, queue, digests, logs, cursor) lives under
`~/.claude/reflection/`, outside the repo. So you can push this to GitHub and share it with
colleagues with zero risk of leaking your own memories.

```
reflect/                      ← this repo (shareable)        ~/.claude/                  ← your data
├── install.sh / uninstall.sh                                ├── skills/{reflect,reflect-review} → symlinks
├── config.example.json                                      ├── settings.json            (hook registered)
├── skills/{reflect,reflect-review}/SKILL.md                 └── reflection/
├── hooks/retrieve.py        ← retrieval hook                    ├── config.json          (generated)
├── bin/run-nightly.sh       ← cron runner                       ├── state.json           (cursor)
└── docs/ARCHITECTURE.md                                          ├── queue/{memories,skills,docs}/
                                                                  ├── store/{memories,docs}/  ← the corpus
                                                                  ├── digests/  └── logs/
```

## Install

Requires: Claude Code CLI on `PATH`, `python3`, `bash`.

```bash
git clone https://github.com/mtthsnc/reflectr && cd reflectr
./install.sh --cron          # skills + data dirs + retrieval hook + nightly cron
```

Flags: `--no-hook` (skip the retrieval hook), `--cron` (install the 02:30 nightly job),
`--force` (overwrite an existing `config.json` with the template). Re-run any time — it's
idempotent, so `git pull && ./install.sh` updates everything in place (skills are symlinked).

Restart open Claude Code sessions afterward so the hook loads.

## Use

- **`/reflect`** — run the distiller now (or let cron do it nightly). Stages candidates, writes a
  digest under `~/.claude/reflection/digests/`, never writes live.
- **`/reflect-review`** — review the queue and promote what you approve into the store.
- After that, just work. The retrieval hook surfaces relevant memories in future prompts on its own.

## Configure

Edit `~/.claude/reflection/config.json` (generated from `config.example.json`):

- `scan.*` — which projects/transcripts to read, min session size, first-run lookback.
- `retrieval.top_k` / `min_score` / `max_chars_per_entry` — how much the hook injects per prompt.
  Set `hook_enabled: false` to mute retrieval without uninstalling.
- `thresholds.*` — caps on candidates per run; how often a workflow must recur to become a skill.

## Uninstall

```bash
./uninstall.sh            # removes skills links, hook, cron — keeps your data
./uninstall.sh --purge    # also deletes ~/.claude/reflection (your memories!)
```

## How retrieval works (and its limits)

`hooks/retrieve.py` is stdlib-only keyword overlap: it weights matches in an entry's `description`
(4×) and `name` (2×) over its body (1×), and injects the top-k above `min_score`. It **never blocks
a prompt** — any error exits silently. It's deliberately simple; swapping in embeddings is the
natural upgrade if keyword recall starts missing synonyms. See `docs/ARCHITECTURE.md`.

## Development

reflectr is self-verifying — two scripts define "correct", and CI runs both on every push/PR:

```bash
./scripts/validate.sh   # conformance gate: shell + shellcheck + ruff + JSON + skill contract
./tests/run.sh          # sandboxed install + retrieval-hook assertions
```

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) (the rules
agents and humans follow when working on the repo). The non-negotiables: no hardcoded paths, skill
descriptions start with "Use when…", and the retrieval hook never blocks a prompt.
