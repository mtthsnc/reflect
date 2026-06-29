import os
import re
import sys

import graph_store as gs

CUES = {
    "works_at": [r"works? at", r"employed (?:at|by)"],
    "invested_in": [r"invested in", r"investor in"],
    "founded": [r"co-?founded", r"founded"],
    "advises": [r"advises?", r"advisor (?:to|of)"],
    "attended": [r"attended"],
}

_WIKILINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def extract_entities(text):
    out = []
    for m in _WIKILINK.finditer(text or ""):
        name = m.group(1).strip()
        if name and name not in out:
            out.append(name)
    return out


def _entities_with_spans(sentence):
    out = []
    for m in _WIKILINK.finditer(sentence):
        out.append((m.group(1).strip(), m.start(), m.end()))
    return out


def _first_entity_after(marks, pos):
    for name, start, _ in marks:
        if start >= pos:
            return name
    return None


def extract_edges(text):
    edges = []
    for sentence in _SENT_SPLIT.split(text or ""):
        marks = _entities_with_spans(sentence)
        if len(marks) < 2:
            continue
        subject = marks[0][0]
        typed = []
        for rel, patterns in CUES.items():
            for pat in patterns:
                for m in re.finditer(r"\b" + pat + r"\b", sentence, re.IGNORECASE):
                    dst = _first_entity_after(marks, m.end())
                    if dst and dst != subject:
                        triple = (subject, rel, dst)
                        if triple not in typed:
                            typed.append(triple)
        if typed:
            for triple in typed:
                if triple not in edges:
                    edges.append(triple)
        else:
            for name, _, _ in marks[1:]:
                triple = (subject, "relates_to", name)
                if triple not in edges:
                    edges.append(triple)
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
    for name in extract_entities(text):
        gs.upsert_node(conn, type="entity", canonical_name=name,
                       provenance=[path], source=source)
    for src_name, rel, dst_name in extract_edges(text):
        src = gs.upsert_node(conn, type="entity", canonical_name=src_name,
                             provenance=[path], source=source)
        dst = gs.upsert_node(conn, type="entity", canonical_name=dst_name,
                             provenance=[path], source=source)
        conf = 1.0 if source == "deterministic" else 0.5
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
