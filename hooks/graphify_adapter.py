import json
import os
import sys

import graph_store as gs


def _node_name(node):
    return str(node.get("label") or node.get("name") or node.get("id"))


def _rel_type(link):
    return str(link.get("type") or link.get("relation") or link.get("label") or "relates_to")


def parse_graph(data):
    raw_nodes = data.get("nodes", []) if isinstance(data, dict) else []
    raw_links = data.get("links", data.get("edges", [])) if isinstance(data, dict) else []
    id_to_name = {}
    nodes = []
    for n in raw_nodes:
        name = _node_name(n)
        id_to_name[n.get("id")] = name
        nodes.append({"name": name, "type": str(n.get("type") or "entity")})
    edges = []
    for link in raw_links:
        src = id_to_name.get(link.get("source"), str(link.get("source")))
        dst = id_to_name.get(link.get("target"), str(link.get("target")))
        confidence = 0.4 if link.get("inferred") else 0.6
        edges.append({"src": src, "dst": dst, "rel_type": _rel_type(link),
                      "confidence": confidence})
    return nodes, edges


def merge_graph(conn, data, provenance=()):
    nodes, edges = parse_graph(data)
    for n in nodes:
        gs.upsert_node(conn, type=n["type"], canonical_name=n["name"],
                       provenance=list(provenance), source="graphify")
    for e in edges:
        src = gs.upsert_node(conn, type="entity", canonical_name=e["src"],
                             provenance=list(provenance), source="graphify")
        dst = gs.upsert_node(conn, type="entity", canonical_name=e["dst"],
                             provenance=list(provenance), source="graphify")
        gs.upsert_edge(conn, src=src, dst=dst, rel_type=e["rel_type"],
                       confidence=e["confidence"], source="graphify",
                       provenance=list(provenance))


def _store_db_path():
    home = os.path.expanduser("~")
    return os.path.join(home, ".claude", "reflection", "store", "graph.sqlite")


def main(argv):
    if not argv:
        return
    path = argv[0]
    provenance = argv[1:]
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    db = _store_db_path()
    os.makedirs(os.path.dirname(db), exist_ok=True)
    conn = gs.connect(db)
    merge_graph(conn, data, provenance=provenance)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except Exception:
        pass
    sys.exit(0)
