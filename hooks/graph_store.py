import json
import sqlite3


def connect(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    _init_schema(conn)
    return conn


def _init_schema(conn):
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS nodes ("
        "  id INTEGER PRIMARY KEY,"
        "  type TEXT,"
        "  canonical_name TEXT UNIQUE,"
        "  aliases TEXT,"
        "  provenance TEXT,"
        "  source TEXT);"
        "CREATE TABLE IF NOT EXISTS edges ("
        "  src INTEGER,"
        "  dst INTEGER,"
        "  rel_type TEXT,"
        "  confidence REAL,"
        "  source TEXT,"
        "  provenance TEXT,"
        "  PRIMARY KEY (src, dst, rel_type));"
    )
    conn.commit()


def _load_list(raw):
    if not raw:
        return []
    try:
        return list(json.loads(raw))
    except Exception:
        return []


def _merge(existing, incoming):
    out = list(existing)
    for item in incoming:
        if item not in out:
            out.append(item)
    return out


def resolve_node(conn, name):
    key = (name or "").strip().lower()
    if not key:
        return None
    for row in conn.execute("SELECT id, canonical_name, aliases FROM nodes"):
        if row["canonical_name"].lower() == key:
            return row["id"]
        if key in [a.lower() for a in _load_list(row["aliases"])]:
            return row["id"]
    return None


def upsert_node(conn, *, type, canonical_name, aliases=(), provenance=(), source="deterministic"):
    existing = resolve_node(conn, canonical_name)
    if existing is None:
        cur = conn.execute(
            "INSERT INTO nodes (type, canonical_name, aliases, provenance, source) VALUES (?,?,?,?,?)",
            (type, canonical_name, json.dumps(list(aliases)),
             json.dumps(list(provenance)), source),
        )
        conn.commit()
        return cur.lastrowid
    row = conn.execute("SELECT * FROM nodes WHERE id=?", (existing,)).fetchone()
    merged_aliases = _merge(_load_list(row["aliases"]), aliases)
    merged_prov = _merge(_load_list(row["provenance"]), provenance)
    new_source = "deterministic" if source == "deterministic" or row["source"] == "deterministic" else row["source"]
    conn.execute(
        "UPDATE nodes SET aliases=?, provenance=?, source=? WHERE id=?",
        (json.dumps(merged_aliases), json.dumps(merged_prov), new_source, existing),
    )
    conn.commit()
    return existing


def upsert_edge(conn, *, src, dst, rel_type, confidence, source, provenance):
    row = conn.execute(
        "SELECT confidence, source, provenance FROM edges WHERE src=? AND dst=? AND rel_type=?",
        (src, dst, rel_type),
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO edges (src, dst, rel_type, confidence, source, provenance) VALUES (?,?,?,?,?,?)",
            (src, dst, rel_type, confidence, source, json.dumps(list(provenance))),
        )
    else:
        merged_prov = _merge(_load_list(row["provenance"]), provenance)
        new_conf = max(row["confidence"], confidence)
        new_source = "deterministic" if source == "deterministic" or row["source"] == "deterministic" else row["source"]
        conn.execute(
            "UPDATE edges SET confidence=?, source=?, provenance=? WHERE src=? AND dst=? AND rel_type=?",
            (new_conf, new_source, json.dumps(merged_prov), src, dst, rel_type),
        )
    conn.commit()


def neighbors(conn, node_id, depth=1, min_confidence=0.0):
    seen = set()
    frontier = {node_id}
    for _ in range(max(0, depth)):
        nxt = set()
        for nid in frontier:
            for row in conn.execute(
                "SELECT src, dst FROM edges WHERE (src=? OR dst=?) AND confidence>=?",
                (nid, nid, min_confidence),
            ):
                other = row["dst"] if row["src"] == nid else row["src"]
                if other not in seen and other != node_id:
                    nxt.add(other)
        seen |= nxt
        frontier = nxt
    return seen


def nodes_for_path(conn, path):
    out = set()
    for row in conn.execute("SELECT id, provenance FROM nodes"):
        if path in _load_list(row["provenance"]):
            out.add(row["id"])
    return out


def provenance_for_nodes(conn, node_ids):
    out = set()
    ids = set(node_ids)
    for row in conn.execute("SELECT id, provenance FROM nodes"):
        if row["id"] in ids:
            out |= set(_load_list(row["provenance"]))
    for row in conn.execute("SELECT src, dst, provenance FROM edges"):
        if row["src"] in ids or row["dst"] in ids:
            out |= set(_load_list(row["provenance"]))
    return out


def all_names(conn):
    names = set()
    for row in conn.execute("SELECT canonical_name, aliases FROM nodes"):
        names.add(row["canonical_name"])
        for a in _load_list(row["aliases"]):
            names.add(a)
    return names


def forget_path(conn, path):
    for row in conn.execute("SELECT id, provenance FROM nodes").fetchall():
        prov = _load_list(row["provenance"])
        if path not in prov:
            continue
        prov = [p for p in prov if p != path]
        if prov:
            conn.execute("UPDATE nodes SET provenance=? WHERE id=?", (json.dumps(prov), row["id"]))
        else:
            conn.execute("DELETE FROM edges WHERE src=? OR dst=?", (row["id"], row["id"]))
            conn.execute("DELETE FROM nodes WHERE id=?", (row["id"],))
    for row in conn.execute("SELECT src, dst, rel_type, provenance FROM edges").fetchall():
        prov = _load_list(row["provenance"])
        if path not in prov:
            continue
        prov = [p for p in prov if p != path]
        if prov:
            conn.execute(
                "UPDATE edges SET provenance=? WHERE src=? AND dst=? AND rel_type=?",
                (json.dumps(prov), row["src"], row["dst"], row["rel_type"]),
            )
        else:
            conn.execute(
                "DELETE FROM edges WHERE src=? AND dst=? AND rel_type=?",
                (row["src"], row["dst"], row["rel_type"]),
            )
    conn.commit()
