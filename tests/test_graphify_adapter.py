import os, tempfile, unittest, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
import graphify_adapter as ga
import graph_store as gs

SAMPLE = {
    "nodes": [
        {"id": 0, "label": "Bob", "type": "person"},
        {"id": 1, "label": "Acme AI", "type": "company"},
    ],
    "links": [
        {"source": 0, "target": 1, "type": "works_at", "inferred": True},
    ],
}


class GraphifyAdapterTest(unittest.TestCase):
    def test_parse_uses_label_as_name(self):
        nodes, edges = ga.parse_graph(SAMPLE)
        names = {n["name"] for n in nodes}
        self.assertEqual(names, {"Bob", "Acme AI"})

    def test_parse_resolves_edge_endpoints_to_names(self):
        nodes, edges = ga.parse_graph(SAMPLE)
        self.assertEqual(edges[0]["src"], "Bob")
        self.assertEqual(edges[0]["dst"], "Acme AI")
        self.assertEqual(edges[0]["rel_type"], "works_at")

    def test_inferred_edges_get_low_confidence(self):
        nodes, edges = ga.parse_graph(SAMPLE)
        self.assertLess(edges[0]["confidence"], 1.0)

    def test_merge_writes_graphify_source(self):
        d = tempfile.mkdtemp()
        conn = gs.connect(os.path.join(d, "graph.sqlite"))
        ga.merge_graph(conn, SAMPLE, provenance=["m1.md"])
        bob = gs.resolve_node(conn, "Bob")
        acme = gs.resolve_node(conn, "Acme AI")
        self.assertIn(acme, gs.neighbors(conn, bob, depth=1))
        row = conn.execute("SELECT source FROM edges").fetchone()
        self.assertEqual(row["source"], "graphify")

    def test_missing_relation_falls_back_to_relates_to(self):
        data = {"nodes": [{"id": 0, "label": "A"}, {"id": 1, "label": "B"}],
                "links": [{"source": 0, "target": 1}]}
        _, edges = ga.parse_graph(data)
        self.assertEqual(edges[0]["rel_type"], "relates_to")


if __name__ == "__main__":
    unittest.main()
