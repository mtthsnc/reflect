# Architecture

## The loop

1. **Capture** — Claude Code writes every session to `~/.claude/projects/<project>/*.jsonl`.
2. **Distill** (`/reflect-stage`, on session end via the SessionEnd hook, or on demand) — reads
   transcripts newer than the cursor in `state.json`, extracts durable signal, and stages
   **proposals** in `queue/`. Writes a digest. Never touches the live store. Advances the cursor last.
3. **Review** (`/reflect`, human-in-the-loop) — the only path from `queue/` → `store/`.
   Promotes approved memories/docs into the store, regenerates `INDEX.md`, clears the queue.
4. **Retrieve** (`hooks/retrieve.py`, every prompt) — scores the prompt against the store and
   injects the top-k matches as context.

Autonomy is **propose-and-approve**: distillation is automatic, promotion is not.

## Push vs. pull (the core design decision)

An earlier shape preloaded a flat `MEMORY.md` index into every session. That cost grows O(n) with
the number of memories — an always-on token tax that also dilutes recall and demands ongoing
pruning/compaction to stay bounded.

`reflect` inverts it. Nothing is preloaded except a constant-size pointer (the registered hook). At
prompt time the hook retrieves the **top-k** relevant entries and injects only those. Consequences:

- Per-prompt context cost is **flat** regardless of store size (only the top-k is ever injected).
- Repeated matches across a session are **deduped**: an entry's full body is injected once, then
  repeat hits emit a one-line pointer until a recency-refresh window elapses — so cost does not grow
  linearly with the number of prompts that happen to match the same entry (see Retrieval scoring).
- The store can grow without compaction — growth no longer touches session context.
- The supervision burden shifts from "prune the index" to "occasionally check retrieval quality,"
  which is smaller and degrades gracefully (a miss = a forgotten fact, not a broken session).

`INDEX.md` still exists, but only as a human browse aid — it is **not** loaded into sessions.

## Retrieval scoring

`retrieve.py` (stdlib only):

1. Read hook JSON on stdin → extract the prompt.
2. Tokenize (lowercase, drop stopwords, len ≥ 3).
3. For each `store/memories/*.md` and `store/docs/*.md`, parse frontmatter and score:
   `4·|q ∩ description| + 2·|q ∩ name| + 1·|q ∩ body|`.
4. Emit entries scoring ≥ `min_score`, top `top_k`, each truncated to `max_chars_per_entry`,
   wrapped in a `<reflect-memory>` block.
5. Dedup against this session's cache (`reflection/cache/<session_id>.json`, keyed by the
   `session_id` in the payload): an entry already injected this session emits a one-line pointer
   instead of its body, unless it hasn't appeared in the last `reinject_after_turns` turns (recency
   refresh). Best-effort — any cache error falls back to full injection. Caches older than a week
   are pruned opportunistically.

The `description` field is the relevance key, so `/reflect-stage` and `/reflect` are told to keep
it specific and keyword-rich. **Upgrade path:** replace step 3 with embedding cosine similarity
(cache vectors next to each entry); the rest of the system is unchanged.

Safety: the hook exits 0 on any error and never writes output it can't bound — it cannot block or
slow a prompt beyond reading a handful of small markdown files.

## Portability

No file in the repo hardcodes a user, home path, or project name.

- Paths default to `~/.claude/...`, which resolves per user.
- `install.sh` generates `config.json` from the template with `$HOME` expanded, symlinks the skills
  into `~/.claude/skills/` (so `git pull` updates them), and merges both hooks (retrieval +
  SessionEnd) into `settings.json` idempotently.
- `on_session_end.py` resolves the `claude` binary via `shutil.which` with the same fallbacks, and is
  recursion-guarded (the `/reflect-stage` run it spawns carries `REFLECT_RUNNING` so its own SessionEnd is a no-op).
- The self-owned `store/` means there are **no** project-specific memory paths — the system is
  identical for every colleague who installs it.

## Files

| Path | Role | Tracked? |
|---|---|---|
| `skills/reflect-stage/SKILL.md` | distiller (queue-only) | yes |
| `skills/reflect/SKILL.md` | review/curate (queue → store) | yes |
| `hooks/retrieve.py` | retrieval hook | yes |
| `hooks/on_session_end.py` | SessionEnd trigger (runs /reflect-stage headless) | yes |
| `config.example.json` | config template | yes |
| `~/.claude/reflection/config.json` | live config | no (generated) |
| `~/.claude/reflection/state.json` | cursor | no |
| `~/.claude/reflection/store/` | the corpus | no |
| `~/.claude/reflection/{queue,digests,logs}/` | working data | no |
