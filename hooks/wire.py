import os
import re
import sys

import graph_store as gs

CANON = {
    "works_at": ["works at", "employed at", "employed by"],
    "founded": ["founded", "cofounded", "co founded"],
    "invested_in": ["invested in", "investor in"],
    "acquired": ["acquired", "bought"],
    "partners_with": ["partners with", "partnered with"],
    "advises": ["advises", "advisor to", "advisor of"],
    "depends_on": ["depends on", "requires", "needs"],
    "built_with": ["built with", "written in", "based on", "uses"],
    "part_of": ["part of", "belongs to", "lives in"],
    "fork_of": ["fork of", "forked from"],
    "configured_by": ["configured by", "pinned to", "set in"],
    "supersedes": ["replaces", "supersedes", "migrated from"],
    "conflicts_with": ["conflicts with", "incompatible with"],
    "fixes": ["fixes", "fixed by", "workaround for"],
    "owned_by": ["owned by", "maintained by"],
    "standard_for": ["standard for", "convention for"],
}

STOP = {"the", "a", "an", "and", "also", "then", "is", "was", "are", "were",
        "be", "been", "that", "this", "it", "its", "as", "our", "their"}

_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_CODE = re.compile(r"`([^`\n]+)`")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\n+")


def _norm_words(span):
    words = re.findall(r"[a-z][a-z0-9+-]*", span.lower())
    return [w for w in words if w not in STOP]


def _build_canon():
    table = {}
    for canon, variants in CANON.items():
        for v in variants:
            key = " ".join(_norm_words(v))
            if key:
                table[key] = canon
    return table


_CANON_BY_PHRASE = _build_canon()


def _relation(span):
    words = _norm_words(span)
    if not words:
        return None
    phrase = " ".join(words)
    if phrase in _CANON_BY_PHRASE:
        return _CANON_BY_PHRASE[phrase]
    return "_".join(words[:3])


def _mentions(text, known):
    spans = []
    for m in _WIKILINK.finditer(text):
        name = m.group(1).strip()
        if name:
            spans.append((name, m.start(), m.end()))
    for m in _CODE.finditer(text):
        tok = m.group(1).strip()
        if tok and " " not in tok:
            spans.append((tok, m.start(), m.end()))
    for name in known:
        for m in re.finditer(r"(?<!\w)" + re.escape(name) + r"(?!\w)", text):
            spans.append((name, m.start(), m.end()))
    spans.sort(key=lambda s: s[1])
    out = []
    seen = set()
    for name, s, e in spans:
        if (s, e) in seen:
            continue
        seen.add((s, e))
        out.append((name, s, e))
    return out


def extract_entities(text, known=()):
    out = []
    for name, _, _ in _mentions(text or "", tuple(known)):
        if name not in out:
            out.append(name)
    return out


def extract_edges(text, known=()):
    known = tuple(known)
    edges = []
    for sentence in _SENT_SPLIT.split(text or ""):
        marks = _mentions(sentence, known)
        if len(marks) < 2:
            continue
        subject = marks[0][0]
        prev_end = marks[0][2]
        for name, start, end in marks[1:]:
            if name == subject:
                prev_end = end
                continue
            rel = _relation(sentence[prev_end:start]) or "relates_to"
            triple = (subject, rel, name)
            if triple not in edges:
                edges.append(triple)
            prev_end = end
    return edges


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def wire_file(conn, path, source="deterministic"):
    gs.forget_path(conn, path)
    text = _read(path)
    if not text:
        return
    known = gs.all_names(conn)
    conf = 1.0 if source == "deterministic" else 0.5
    for name in extract_entities(text, known):
        gs.upsert_node(conn, type="entity", canonical_name=name,
                       provenance=[path], source=source)
    for src_name, rel, dst_name in extract_edges(text, known):
        src = gs.upsert_node(conn, type="entity", canonical_name=src_name,
                             provenance=[path], source=source)
        dst = gs.upsert_node(conn, type="entity", canonical_name=dst_name,
                             provenance=[path], source=source)
        gs.upsert_edge(conn, src=src, dst=dst, rel_type=rel,
                       confidence=conf, source=source, provenance=[path])


def _store_db_path():
    home = os.path.expanduser("~")
    return os.path.join(home, ".claude", "reflection", "store", "graph.sqlite")


def _memories_dir():
    home = os.path.expanduser("~")
    return os.path.join(home, ".claude", "reflection", "store", "memories")


def main(argv):
    db = _store_db_path()
    os.makedirs(os.path.dirname(db), exist_ok=True)
    conn = gs.connect(db)
    if argv and argv[0] == "--rebuild":
        conn.execute("DELETE FROM edges")
        conn.execute("DELETE FROM nodes")
        conn.commit()
        root = _memories_dir()
        for base, _, names in os.walk(root):
            for n in names:
                if n.endswith(".md") and n != "INDEX.md":
                    wire_file(conn, os.path.join(base, n))
        return
    for path in argv:
        wire_file(conn, path)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:
        pass
    sys.exit(0)
