# reflectr

[![CI](https://github.com/mtthsnc/reflectr/actions/workflows/ci.yml/badge.svg)](https://github.com/mtthsnc/reflectr/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A memory for [Claude Code](https://claude.com/claude-code) that improves itself.** reflectr reads
back over your sessions, distills what's worth keeping into proposals you approve, and then quietly
surfaces the right knowledge in future prompts — so each day's work compounds instead of evaporating.

```
 sessions  ──/reflect──▶  queue  ──/reflect-review──▶  store  ──retrieval hook──▶  future
 (.jsonl)    distill,      (you      promote          (memories   top-k injected     prompts
             nightly       approve)                    + docs)     per prompt
             or on demand)
```

You stay in control: the loop only ever *proposes*, and your knowledge lives as plain markdown in
your own filesystem — never preloaded wholesale, never shipped to a server.

---

- [Quickstart](#quickstart)
- [How it works](#how-it-works)
- [A worked example](#a-worked-example)
- [The workflow](#the-workflow)
- [What's inside](#whats-inside)
- [Why it scales](#why-it-scales)
- [Install](#install) · [Configure](#configure) · [Uninstall](#uninstall)
- [Retrieval internals](#retrieval-internals)
- [Engine vs. data](#engine-vs-data) (your privacy)
- [Development](#development) · [Philosophy](#philosophy) · [Contributing](#contributing)

## Quickstart

Requires the Claude Code CLI on your `PATH`, plus `python3` and `bash`.

```bash
git clone https://github.com/mtthsnc/reflectr && cd reflectr
./install.sh --cron     # skills + data dirs + retrieval hook + nightly job
```

Restart any open Claude Code sessions so the hook loads. That's it — reflectr now runs nightly and
retrieves on its own. Run `/reflect` any time to distill immediately, and `/reflect-review` to
approve what it found.

## How it works

It starts the moment you stop for the day. While you're away (or whenever you run `/reflect`),
reflectr reads back over your recent Claude Code sessions — not the raw tool-noise, but what actually
happened: what you were trying to do, where things went sideways, the preferences and decisions worth
remembering. It writes those up as **proposals** and sets them aside with a short digest. Nothing has
touched your knowledge base yet.

When you're ready, you run `/reflect-review`. Here you're the editor: approve the sharp ones, drop the
noise, tweak wording. Only what you approve moves into your **store**.

From then on you do nothing. Each time you send a prompt, a hook quietly checks your store and, if
something is relevant, slips the **top few** matching entries into Claude's context — just those,
never the whole pile. The store can grow for years while what Claude sees each turn stays small.

Because retrieval is automatic, there's nothing to remember and nothing to maintain.

## A worked example

**1. `/reflect` proposes a memory** after a session where you talked through frontend conventions. It
lands in the queue as a small markdown file:

```markdown
---
name: project-frontend-context-protocol
description: User's interest in a Frontend Context Protocol — engineering conventions as code, conformance gates, self-verifying
metadata:
  type: project
---
Frontend analog of a Brand Context Protocol: design tokens + component API conventions +
a11y/code-style rules + ADRs codified as machine-readable files, paired with automated
conformance gates whose failures feed back to refine the spec.
```

**2. `/reflect-review` shows it to you.** You approve; it moves into `store/memories/`. (The
`description` line matters — it's what retrieval scores against, so it's kept specific and keyword-rich.)

**3. Days later you open a prompt** that mentions frontend conventions. *Before* Claude answers, the
hook injects just the relevant entry:

```
<reflect-memory>
## project-frontend-context-protocol
_User's interest in a Frontend Context Protocol — engineering conventions as code…_
Frontend analog of a Brand Context Protocol: design tokens + component API conventions …
</reflect-memory>
```

You didn't load anything. You didn't even remember the memory existed. It was simply there.

## The workflow

1. **`/reflect`** — the distiller. Reads new session transcripts since the last run and stages
   proposed memories, skills, and docs in a queue, plus a daily digest. **Queue-only** — it never
   writes to your live store. Runs nightly via cron, or on demand.

2. **`/reflect-review`** — the curator. Walks you through the queue; you accept, edit, or reject each
   item. Approved items are promoted into the store and the browse index is regenerated. This is the
   **only** path from queue to live.

3. **the retrieval hook** — invisible. On every prompt it scores your store and injects the top-k
   relevant entries. No command, no thought required.

## What's inside

**Skills** (symlinked into `~/.claude/skills/` on install)
- **reflect** — the nightly distiller (transcripts → staged proposals + digest)
- **reflect-review** — the approval step (queue → store)

**Engine**
- **hooks/retrieve.py** — the `UserPromptSubmit` retrieval hook (stdlib-only, never blocks a prompt)
- **bin/run-nightly.sh** — the cron runner (resolves the `claude` binary at runtime)
- **install.sh / uninstall.sh** — idempotent wiring into `~/.claude/`
- **config.example.json** — the config template

**Quality**
- **scripts/validate.sh** — conformance gate (shell · shellcheck · ruff · JSON · skill contract)
- **tests/run.sh** — sandboxed install + retrieval-hook assertions
- **CI** runs both on every push and PR

## Why it scales

The store is **pulled, not preloaded**. Older "load all memories every session" designs grow an
always-on context tax and need constant pruning. reflectr instead scores each prompt against every
entry's `description` and injects only the top-k matches. The corpus can grow to thousands of entries
while per-session cost stays flat — and there's no index to babysit.

## Install

```bash
git clone https://github.com/mtthsnc/reflectr && cd reflectr
./install.sh --cron
```

Flags:

| Flag | Effect |
|---|---|
| *(none)* | skills + data dirs + retrieval hook |
| `--cron` | also install the 02:30 nightly job |
| `--no-hook` | skip the retrieval hook |
| `--force` | overwrite an existing `config.json` with the template |

It's idempotent — re-run any time. `git pull && ./install.sh` updates everything in place (skills are
symlinked, so they update on pull). Restart open Claude Code sessions afterward so the hook loads.

## Configure

Edit `~/.claude/reflection/config.json` (generated from `config.example.json`):

- **`scan.*`** — which projects/transcripts to read, minimum session size, first-run lookback.
- **`retrieval.top_k` / `min_score` / `max_chars_per_entry`** — how much the hook injects per prompt.
  Set `hook_enabled: false` to mute retrieval without uninstalling.
- **`thresholds.*`** — caps on candidates per run; how often a workflow must recur to become a skill.

## Uninstall

```bash
./uninstall.sh            # removes skills links, hook, cron — keeps your data
./uninstall.sh --purge    # also deletes ~/.claude/reflection (your memories!)
```

## Retrieval internals

`hooks/retrieve.py` is stdlib-only keyword overlap: it weights matches in an entry's `description`
(4×) and `name` (2×) over its body (1×) and injects the top-k above `min_score`. It **never blocks a
prompt** — any error path exits silently with no output. It's deliberately simple; swapping in
embedding similarity is the natural upgrade if keyword recall starts missing synonyms. Full design in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Engine vs. data

This repo is the **engine** — skills, scripts, the hook, the config template. It contains **no
personal data**. Everything you generate lives under `~/.claude/`, outside the repo, and is
gitignored. You can push your fork to GitHub and share it with colleagues with zero risk of leaking
your own memories.

```
This repo — the engine (safe to share)
──────────────────────────────────────
reflectr/
├── skills/
│   ├── reflect/SKILL.md           the nightly distiller
│   └── reflect-review/SKILL.md    the approval step
├── hooks/retrieve.py              retrieval hook (stdlib only)
├── bin/run-nightly.sh             cron runner
├── scripts/validate.sh            conformance gate
├── tests/run.sh                   test suite
├── config.example.json            config template
├── install.sh · uninstall.sh      idempotent wiring
└── docs/ARCHITECTURE.md
```

```
~/.claude/ — your data (never committed)
────────────────────────────────────────
~/.claude/
├── skills/{reflect,reflect-review} → symlinks into this repo
├── settings.json                     retrieval hook registered here
└── reflection/
    ├── config.json     generated from the template
    ├── state.json      cursor — which sessions are processed
    ├── store/
    │   ├── memories/   the corpus the hook retrieves from
    │   └── docs/
    ├── queue/          staged proposals, awaiting review
    ├── digests/        daily human-readable summaries
    └── logs/
```

## Development

reflectr is self-verifying — two scripts define "correct", and CI runs both on every push/PR:

```bash
./scripts/validate.sh   # conformance gate: shell + shellcheck + ruff + JSON + skill contract
./tests/run.sh          # sandboxed install + retrieval-hook assertions
```

See [CONTRIBUTING.md](CONTRIBUTING.md) to set up the linters and pre-commit hooks, and
[AGENTS.md](AGENTS.md) for the rules agents and humans follow when working on the repo.

## Philosophy

- **Propose, then approve.** The loop drafts; you decide. Nothing goes live unreviewed.
- **Pull, don't preload.** Retrieve what's relevant per prompt; never tax every session with the
  whole store.
- **Own your knowledge.** Plain markdown in your filesystem — no vendor lock-in, no SaaS dashboard.
- **Self-verifying.** Conformance gates and tests define correctness; CI enforces it.
- **Signal over volume.** A few sharp memories beat a pile of vague notes.

## Contributing

Contributions welcome. The non-negotiables: no hardcoded paths, skill descriptions start with
"Use when…", and the retrieval hook never blocks a prompt.

1. Fork and branch off `main`.
2. Make your change; keep `./scripts/validate.sh` and `./tests/run.sh` green.
3. Note user-facing changes in [CHANGELOG.md](CHANGELOG.md) under "Unreleased".
4. Open a PR using the template — CI must pass.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full guide and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

[MIT](LICENSE).
