---
name: recall
description: Use when the user asks a question that should be answered from their reflect memory (who/what/when across people, tools, projects, and decisions) and wants a synthesized, cited answer rather than raw matches.
---

# recall

## Overview

Answer a question from the reflect knowledge store by traversing the graph to find the relevant memories, then synthesizing a cited answer with an explicit note on what the store does not yet contain. The graph is the entrypoint; the memory files are the source of truth and the citation target.

## Procedure

1. Resolve the entities named in the question against the graph:

       python3 "$(dirname "$(readlink -f ~/.claude/skills/recall)")/../hooks/graph_store.py" 2>/dev/null

   (Import `graph_store` and call `resolve_node`/`neighbors`/`provenance_for_nodes` against `~/.claude/reflection/store/graph.sqlite`.)

2. Traverse typed edges from each resolved entity to gather connected nodes relevant to the question.

3. Collect the provenance memory files for the touched nodes and edges. Read those files from `~/.claude/reflection/store/memories/`.

4. Write the answer in exactly three parts:
   - **Answer:** synthesized prose that directly addresses the question.
   - **Citations:** for each claim, the memory file(s) that back it (path under `store/memories/`).
   - **What reflect does not know yet:** computed from unresolved query entities, edges below the configured `min_confidence`, and entity neighborhoods whose provenance is thin or rests only on `source=graphify` edges.

## Common mistakes

- Answering from raw keyword matches instead of graph traversal.
- Citing a memory that was retrieved but does not actually support the claim.
- Omitting the gap note when the graph has no path to the asked entity. The gap note is mandatory and is the point of the command.

## Guardrails

- Never assert a fact whose only support is a `source=graphify` (inferred) edge without labeling it as inferred.
- Read-only: `/recall` never writes to the store or the graph.
