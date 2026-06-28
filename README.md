# reflect

[![CI](https://github.com/mtthsnc/reflect/actions/workflows/ci.yml/badge.svg)](https://github.com/mtthsnc/reflect/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A memory for [Claude Code](https://claude.com/claude-code) that improves itself.** reflect reads
back over your sessions, distills what's worth keeping into proposals you approve, and then quietly
surfaces the right knowledge in future prompts — so each day's work compounds instead of evaporating.

<p align="center">
  <img src="assets/demo.gif" width="760"
       alt="The reflect loop: /reflect distills sessions, /reflect-curate promotes approved memories, and a later session shows the retrieval hook injecting one automatically">
  <br>
  <sub><i>The whole loop — <code>/reflect</code> distills the day's sessions, <code>/reflect-curate</code> promotes what you approve, and a week later the hook recalls it on its own.</i></sub>
</p>

You stay in control: the loop only ever *proposes*, and your knowledge lives as plain markdown in
your own filesystem — never preloaded wholesale, never shipped to a server.

---

- [Quickstart](#quickstart)
- [How it works](#how-it-works)
- [Anatomy of a memory](#anatomy-of-a-memory)
- [The three commands](#the-three-commands)
- [What's inside](#whats-inside)
- [Why it scales](#why-it-scales)
- [vs. Claude Code's built-in memory](#vs-claude-codes-built-in-memory)
- [Install](#install) · [Configure](#configure) · [Uninstall](#uninstall)
- [Retrieval internals](#retrieval-internals)
- [Engine vs. data](#engine-vs-data) (your privacy)
- [Development](#development) · [Philosophy](#philosophy) · [Contributing](#contributing)

## Quickstart

Requires the Claude Code CLI on your `PATH`, plus `python3` and `bash`.

```bash
git clone https://github.com/mtthsnc/reflect && cd reflect
./install.sh     # skills + data dirs + retrieval & session-end hooks
```

Restart any open Claude Code sessions so the hooks load. That's it — reflect now distills
automatically when a session ends (`/clear` or exit) and retrieves on its own. Run `/reflect` any
time to distill immediately, and `/reflect-curate` to approve what it found.

## How it works

It starts the moment a session ends. When you `/clear` or exit (or whenever you run `/reflect`),
reflect reads back over your recent Claude Code sessions — not the raw tool-noise, but what actually
happened: what you were trying to do, where things went sideways, the preferences and decisions worth
remembering. It writes those up as **proposals** and sets them aside with a short digest. Nothing has
touched your knowledge base yet.

When you're ready, you run `/reflect-curate`. Here you're the editor: approve the sharp ones, drop the
noise, tweak wording. Only what you approve moves into your **store**.

From then on you do nothing. Each time you send a prompt, a hook quietly checks your store and, if
something is relevant, slips the **top few** matching entries into Claude's context — just those,
never the whole pile. The store can grow for years while what Claude sees each turn stays small.

```
 sessions  ──/reflect──▶  queue  ──/reflect-curate──▶  store  ──retrieval hook──▶  future
 (.jsonl)    distill on    (you      promote          (memories   top-k injected     prompts
             session-end   approve)                    + docs)     per prompt
             or on demand)
```

## Anatomy of a memory

The animation above shows the flow; here's what the actual artifacts look like.

A staged memory is a small markdown file. Its `description` is the **retrieval key** — the hook scores
your prompts against it, so it's written to be specific and keyword-rich:

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

You approve it in `/reflect-curate`; it moves into `store/memories/`. Then, days later, a prompt that
touches the topic makes the hook inject *just that entry* — before Claude even starts answering:

```
<reflect-memory>
## project-frontend-context-protocol
_User's interest in a Frontend Context Protocol — engineering conventions as code…_
Frontend analog of a Brand Context Protocol: design tokens + component API conventions …
</reflect-memory>
```

You didn't load anything. You didn't even remember the memory existed. It was simply there.

## The three commands

| | Role | What it does |
|---|---|---|
| **`/reflect`** | distiller | Reads new transcripts since the last run, stages proposed memories/skills/docs + a digest. **Queue-only** — never writes live. On session end (`/clear` or exit), or on demand. |
| **`/reflect-curate`** | curator | Walks the queue; you accept, edit, or reject each item. Promotes the approved ones and regenerates the index. The **only** path from queue to live. |
| **retrieval hook** | recall | On every prompt, scores the store and injects the top-k relevant entries. Invisible — no command, nothing to remember. |

## What's inside

**Skills** (symlinked into `~/.claude/skills/` on install)
- **reflect** — the distiller (transcripts → staged proposals + digest)
- **reflect-curate** — the approval step (queue → store)

**Engine**
- **hooks/retrieve.py** — the `UserPromptSubmit` retrieval hook (stdlib-only, never blocks a prompt)
- **hooks/on_session_end.py** — the `SessionEnd` hook (runs `/reflect` headless on session end)
- **install.sh / uninstall.sh** — idempotent wiring into `~/.claude/`
- **config.example.json** — the config template

**Quality**
- **scripts/validate.sh** — conformance gate (shell · shellcheck · ruff · JSON · skill contract)
- **tests/run.sh** — sandboxed install + retrieval-hook assertions
- **CI** runs both on every push and PR

## Why it scales

The store is **pulled, not preloaded**. Older "load all memories every session" designs grow an
always-on context tax and need constant pruning. reflect instead scores each prompt against every
entry's `description` and injects only the top-k matches. The corpus can grow to thousands of entries
while per-session cost stays flat — and there's no index to babysit.

## vs. Claude Code's built-in memory

Claude Code ships its own [auto memory](https://docs.claude.com/en/docs/claude-code/memory) (on by
default, v2.1.59+): Claude writes notes for itself as it works, kept in a per-repository `MEMORY.md`
index plus topic files it reads on demand. The two systems are **more alike than the names suggest**
— both bound per-session context instead of loading everything. The real differences are about *who
curates*, *how recall is triggered*, and *what's stored*:

| | Auto memory | reflect |
|---|---|---|
| **Who writes it** | Claude, automatically — it decides what's worth saving | Claude proposes; **you approve** each item in `/reflect-curate` |
| **When captured** | Mid-session, from your corrections and preferences | Batch pass over whole past transcripts (on session end or on demand) |
| **Always-on context** | The `MEMORY.md` index — first 200 lines / 25 KB, every session | None — nothing loads until a prompt matches |
| **Recall** | Index is preloaded; Claude opens topic files on demand when it judges them relevant | A hook keyword-scores every entry per prompt and injects the top-k, regardless of what the model decides |
| **Scope** | Per git repository, machine-local | One store across all your projects |
| **What it stores** | Memory notes — build commands, debugging insights, preferences | Typed memories, docs, and promotable **skills** |
| **Maintenance** | None — it just works | You curate the queue; an unreviewed queue is dead weight |

**The honest summary:** these overlap more than the framing suggests — auto memory is already bounded
(it caps the always-loaded index and lazy-loads the rest), so reflect's edge is *not* "we pull and
they preload everything." It's narrower and more specific: the **approval gate** (nothing lands
unreviewed), **deterministic per-prompt injection** (recall doesn't hinge on the model choosing to
open a file), **transcript distillation** (it mines whole sessions, not just in-the-moment
corrections), a **cross-project** store rather than per-repo, and that it promotes reusable
**skills**, not just notes. If you want zero-effort memory scoped to one repo, auto memory is the
better fit. reflect trades that effort for control, cross-project recall, and skills.

## Install

```bash
git clone https://github.com/mtthsnc/reflect && cd reflect
./install.sh
```

Flags:

| Flag | Effect |
|---|---|
| *(none)* | skills + data dirs + retrieval & session-end hooks |
| `--no-hook` | skip both hooks |
| `--force` | overwrite an existing `config.json` with the template |

It's idempotent — re-run any time. `git pull && ./install.sh` updates everything in place (skills are
symlinked, so they update on pull). Restart open Claude Code sessions afterward so the hooks load.

## Configure

Edit `~/.claude/reflection/config.json` (generated from `config.example.json`):

- **`scan.*`** — which projects/transcripts to read, minimum session size, first-run lookback.
- **`retrieval.top_k` / `min_score` / `max_chars_per_entry`** — how much the hook injects per prompt.
  Set `hook_enabled: false` to mute retrieval without uninstalling.
- **`thresholds.*`** — caps on candidates per run; how often a workflow must recur to become a skill.

## Uninstall

```bash
./uninstall.sh            # removes skills links and both hooks — keeps your data
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
reflect/
├── skills/
│   ├── reflect/SKILL.md           the distiller
│   └── reflect-curate/SKILL.md    the approval step
├── hooks/retrieve.py              retrieval hook (stdlib only)
├── hooks/on_session_end.py        SessionEnd trigger (runs /reflect headless)
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
├── skills/{reflect,reflect-curate} → symlinks into this repo
├── settings.json                     both hooks registered here
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

reflect is self-verifying — two scripts define "correct", and CI runs both on every push/PR:

```bash
./scripts/validate.sh   # conformance gate: shell + shellcheck + ruff + JSON + skill contract
./tests/run.sh          # sandboxed install + retrieval-hook assertions
```

The README demo is reproducible: `python3 assets/make-cast.py` regenerates the cast, then `agg`
renders it to `assets/demo.gif`. See [CONTRIBUTING.md](CONTRIBUTING.md) to set up the
linters and pre-commit hooks, and [AGENTS.md](AGENTS.md) for the rules agents and humans follow when
working on the repo.

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
