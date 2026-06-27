---
name: reflect
description: Use when distilling recent Claude Code session transcripts into proposed memories, skills, and docs — the nightly learning pass, or on demand. Stages candidates in a review queue only; approval is the separate /reflect-curate step.
---

# Reflect — the daily learning loop

## Overview

The distiller half of a propose-and-approve learning loop. Turn raw session transcripts into
durable, reusable knowledge — **as proposals only**. Nothing here goes live.

You are the reflection engine for a continuous-learning system. Your job: turn raw session
transcripts into durable, reusable knowledge — **as proposals only**. Nothing you produce here
goes live. You stage candidates in a queue and write a digest; the human approves later via
`/reflect-curate`.

Optimize for **signal over volume**. A run that proposes 2 sharp memories and 1 real skill beats
one that dumps 15 vague notes. Junk that survives review pollutes every future session.

All paths come from config — never hardcode an absolute user path. The one fixed anchor is the
config file itself at `~/.claude/reflection/config.json`; read every other path from it.

## Inputs

- Config: `~/.claude/reflection/config.json` (resolve `~` to the current user's home)
- State (cursor): `~/.claude/reflection/state.json`
- Source transcripts: `*.jsonl` under `config.scan.projects_root/<project>/`
- Existing knowledge (for dedup): `config.targets.memories_dir`, `config.targets.docs_dir`,
  `config.targets.store_index`, and `config.targets.skills_dir`

## Procedure

### 1. Load state and config
Read `config.json` and `state.json`. Determine the cutoff:
- If `state.last_processed_mtime > 0`, process transcripts with mtime strictly newer than it.
- Otherwise (first run / null), process transcripts modified within the last
  `scan.lookback_hours_if_no_state` hours.

### 2. Select new sessions
List `*.jsonl` files under each included project dir (respect `include_projects` /
`exclude_projects`; `["*"]` means all). Keep a file only if **all** hold:
- mtime newer than the cutoff,
- size ≥ `scan.min_session_bytes` (skip trivial sessions),
- its session id (filename without `.jsonl`) is **not** in `state.processed_sessions`.

Use `find <projects_root> -name '*.jsonl' -newermt <cutoff>` plus `ls -la` for mtimes. If there
are zero new sessions, write a one-line "nothing new" digest for today, update `last_run_iso`,
and stop — do not invent content.

### 3. Read existing knowledge (dedup baseline)
Before extracting anything, list `memories_dir` and skim the memory files, read `store_index`, and
list the skills dir. You must dedup every candidate against what already exists. Updating/sharpening
an existing memory is allowed and encouraged — flag those as `action: update` with the target
filename. The `description:` field is the retrieval key (the hook scores prompts against it) — make
it specific and keyword-rich.

### 4. Read the new transcripts
Each line of a `.jsonl` is one event (user msg, assistant msg, tool call, tool result). Read for
**meaning**, skim tool-output noise. Per session, extract:
- **What the user was trying to do** and whether it worked.
- **Friction**: repeated corrections, things you got wrong, preferences the user stated.
- **Reusable procedures**: multi-step workflows the user drove or you executed that could recur.
- **Durable facts**: who the user is, their stack, conventions, external resources, decisions.

### 5. Produce candidates (apply thresholds from config)

**Memories** → `<queue_dir>/memories/<slug>.md`. One fact per file, using the exact memory
frontmatter contract:
```markdown
---
name: <short-kebab-case-slug>
description: <one-line summary, keyword-rich — this is the retrieval relevance key>
metadata:
  type: user | feedback | project | reference
  source_sessions: [<session-id>, ...]
  proposed: <today's date YYYY-MM-DD>
  action: create | update
  target: <existing-filename-if-update>
---

<the fact. For feedback/project add **Why:** and **How to apply:** lines. Link related with [[name]].>
```
Cap at `thresholds.max_memory_candidates_per_run`. Do not propose anything the repo/git/CLAUDE.md
already records, or anything that only mattered to one conversation.

**Skills** → `<queue_dir>/skills/<name>/SKILL.md`. Only propose a skill if the underlying workflow
appeared at least `thresholds.skill_min_repeat_count` times (across this run or vs. existing
memories/history) OR the user explicitly asked to make it repeatable. Each gets valid skill
frontmatter (`name`, `description`) plus a `PROPOSAL.md` sibling explaining the evidence (which
sessions, why it recurs, what it would replace). Cap at `max_skill_candidates_per_run`.

**Docs** → `<queue_dir>/docs/<slug>.md`. Longer-form playbooks/decisions/notes too big for a memory.
Start each with a short `> Proposed YYYY-MM-DD · sources: ...` line. Cap at `max_doc_candidates_per_run`.

If a queue file with the same name already exists from a prior un-reviewed run, overwrite it with
the merged/better version rather than creating duplicates.

### 6. Write the daily digest
`~/.claude/reflection/digests/<YYYY-MM-DD>.md`. The human-facing summary. Format:
```markdown
# Reflection digest — <YYYY-MM-DD>

## Yesterday → today
What was worked on in the processed sessions, and what this run improved in the knowledge base.

## Worked on
- <session-level bullets: what the user did, outcomes>

## Proposed this run
### Memories (N)
- <slug> — <one-liner> [create|update]
### Skills (N)
- <name> — <one-liner> (evidence: sessions …)
### Docs (N)
- <slug> — <one-liner>

## Patterns & friction noticed
- <recurring themes, repeated corrections, preferences — even if not yet a candidate>

## Nothing-yet
- <signals too weak to propose, worth watching if they recur>

## Review
Run `/reflect-curate` to approve or reject the N items above.
```

### 7. Advance the cursor (do this LAST, only after queue + digest are written)
Update `state.json`:
- `last_run_iso` = now (ISO 8601),
- `last_processed_mtime` = the **max mtime** among sessions processed this run (leave unchanged if none),
- append processed session ids to `processed_sessions` (keep unique; cap to last ~500),
- append a run record to `runs`: `{iso, sessions_processed, memories, skills, docs}` (keep last ~90).

Append a one-line summary to `~/.claude/reflection/logs/reflect.log`.

## Output to the user
End with a terse summary: sessions processed, candidates proposed by type, and a pointer to run
`/reflect-curate`. Do not gush. If nothing new, say so in one line.

## Common mistakes
- **Writing live.** This skill is queue-only. Promotion happens in `/reflect-curate`, never here.
- **Volume over signal.** 15 vague notes is failure, not thoroughness. Junk that survives review
  pollutes every future retrieval.
- **Advancing the cursor early.** If the queue/digest write fails, the cursor must NOT move, or those
  sessions are lost forever.
- **Re-proposing what already exists.** Dedup against the store first; sharpen via `action: update`.
- **Weak `description` fields.** The retrieval hook scores prompts against `description` — a vague
  one means the memory is never surfaced. Make it specific and keyword-rich.

## Guardrails
- NEVER write to the live store (`memories_dir`/`docs_dir`), skills dir, or `store_index` from this
  skill. Queue only.
- NEVER advance the cursor before the queue and digest are successfully written.
- Prefer updating an existing memory over creating a near-duplicate.
- When unsure whether something is durable, put it under "Nothing-yet" in the digest, not the queue.
