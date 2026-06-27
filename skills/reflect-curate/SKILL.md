---
name: reflect-curate
description: Use when curating the queue: reviewing the candidates /reflect staged and promoting the approved ones into the live knowledge store — the only path from queue to live. Run after /reflect, or whenever the queue holds unreviewed items.
---

# Reflect-curate — review & promote the queue

## Overview

The curator half of the loop. Promote staged candidates into the live store — the **only** path
from `queue/` → `store/`. The human decides; you present clearly and execute choices precisely.

You promote staged reflection candidates into the live knowledge store. The human decides; you
present clearly and execute their choices precisely. This is the only path from queue → live.

All paths come from config. The one fixed anchor is `~/.claude/reflection/config.json`; read every
other path from it (resolve `~` to the current user's home).

## Inputs
- Config: `~/.claude/reflection/config.json` (for live target paths)
- Queue: `<queue_dir>/{memories,skills,docs}/`

## Procedure

### 1. Load and present the queue
Read every candidate in the three queue subdirs. For each, show a compact card:
- type, name/slug, the `description`, and for memories the `metadata.type` + `action`.
- For skills, also show the `PROPOSAL.md` evidence (why it recurs, what it replaces).
- For `update` memories, show a diff vs. the existing target file so the change is reviewable.

Group by type. If the queue is empty, say so and stop.

### 2. Ask for decisions
Present the list and ask the user to approve all, reject all, or pick per-item (accept / edit /
reject). Honor edits — apply the user's wording before promoting. Default to NOT promoting anything
the user didn't explicitly accept.

### 3. Promote approved items
- **Memories** → write into `config.targets.memories_dir`. Strip the reflection-only frontmatter
  keys (`source_sessions`, `proposed`, `action`, `target`) so the live file matches the standard
  memory contract (`name`, `description`, `metadata.type`). For `action: update`, edit the existing
  target file instead of creating a new one. Keep `description` keyword-rich — it is the retrieval
  key the hook scores prompts against.
- **Skills** → copy the candidate dir (SKILL.md only; drop `PROPOSAL.md`) into
  `config.targets.skills_dir/<name>/`. Verify frontmatter has valid `name` + `description`.
- **Docs** → move into `config.targets.docs_dir/` (strip the `> Proposed …` line or keep it as
  provenance, user's choice).

### 4. Regenerate the store index
After promotions, rewrite `config.targets.store_index` (`INDEX.md`) as a browsable list of every
live memory and doc — one line each: `- [name](relative/path.md) — description`. This index is a
human/browse aid ONLY; it is **not** loaded into sessions (retrieval is handled by the hook scoring
`description` fields), so it can grow without bounding session context. Group by `metadata.type`.

### 5. Clear processed items
Delete approved AND explicitly-rejected candidates from the queue. Leave deferred ("decide later")
items in place. Append a line to `~/.claude/reflection/logs/review.log` recording what was
promoted/rejected and when.

## Output
Summarize: what was promoted (with live paths), what was rejected, what remains queued. Confirm the
INDEX was regenerated. Remind the user the retrieval hook will surface these in future prompts
automatically — no per-session loading needed.

## Common mistakes
- **Promoting by default.** Only the items the user accepted in THIS review go live. Silence ≠ yes.
- **Leaving reflection-only frontmatter in live files.** Strip `source_sessions`, `proposed`,
  `action`, `target` — a live memory must match the standard contract exactly or it won't load.
- **Creating a near-duplicate instead of updating.** For `action: update`, edit the target file.
- **Forgetting the INDEX.** Regenerate `store_index` after promotions so the browse view stays true.
- **Not clearing the queue.** Approved AND rejected items must be removed, or the next review
  re-shows them.

## Guardrails
- Only promote items the user accepted in THIS review.
- Match each live format's contract exactly — a malformed skill or memory frontmatter breaks loading.
- Prefer editing an existing memory (action: update) over creating a near-duplicate.
- Dangling `[[links]]` to non-promoted memories are harmless; mention them but don't block on them.
