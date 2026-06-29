import os, tempfile, unittest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
import graph_store as gs


class GraphStoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "graph.sqlite")
        self.conn = gs.connect(self.db)

    def test_upsert_node_dedupes_on_canonical_name(self):
        a = gs.upsert_node(self.conn, type="person", canonical_name="Bob", provenance=["m1.md"])
        b = gs.upsert_node(self.conn, type="person", canonical_name="Bob", provenance=["m2.md"])
        self.assertEqual(a, b)

    def test_resolve_matches_alias_case_insensitively(self):
        nid = gs.upsert_node(self.conn, type="company", canonical_name="Acme AI", aliases=["Acme"])
        self.assertEqual(gs.resolve_node(self.conn, "acme"), nid)

    def test_neighbors_traverses_edges(self):
        bob = gs.upsert_node(self.conn, type="person", canonical_name="Bob", provenance=["m1.md"])
        acme = gs.upsert_node(self.conn, type="company", canonical_name="Acme", provenance=["m1.md"])
        gs.upsert_edge(self.conn, src=bob, dst=acme, rel_type="works_at",
                       confidence=1.0, source="deterministic", provenance=["m1.md"])
        self.assertIn(acme, gs.neighbors(self.conn, bob, depth=1))

    def test_neighbors_respects_confidence_floor(self):
        a = gs.upsert_node(self.conn, type="x", canonical_name="A")
        b = gs.upsert_node(self.conn, type="x", canonical_name="B")
        gs.upsert_edge(self.conn, src=a, dst=b, rel_type="relates_to",
                       confidence=0.4, source="graphify", provenance=[])
        self.assertNotIn(b, gs.neighbors(self.conn, a, depth=1, min_confidence=0.5))

    def test_provenance_round_trips_through_paths(self):
        bob = gs.upsert_node(self.conn, type="person", canonical_name="Bob", provenance=["m1.md"])
        self.assertIn(bob, gs.nodes_for_path(self.conn, "m1.md"))
        self.assertIn("m1.md", gs.provenance_for_nodes(self.conn, {bob}))

    def test_forget_path_removes_orphans(self):
        bob = gs.upsert_node(self.conn, type="person", canonical_name="Bob", provenance=["m1.md"])
        gs.forget_path(self.conn, "m1.md")
        self.assertIsNone(gs.resolve_node(self.conn, "Bob"))

    def test_node_merge_unions_aliases_and_provenance(self):
        gs.upsert_node(self.conn, type="company", canonical_name="Acme", aliases=["Acme AI"], provenance=["m1.md"])
        nid = gs.upsert_node(self.conn, type="company", canonical_name="Acme", aliases=["ACME"], provenance=["m2.md"])
        row = self.conn.execute("SELECT aliases, provenance FROM nodes WHERE id=?", (nid,)).fetchone()
        self.assertEqual(set(__import__("json").loads(row["aliases"])), {"Acme AI", "ACME"})
        self.assertEqual(set(__import__("json").loads(row["provenance"])), {"m1.md", "m2.md"})

    def test_edge_merge_takes_max_confidence_and_unions_provenance(self):
        a = gs.upsert_node(self.conn, type="x", canonical_name="A")
        b = gs.upsert_node(self.conn, type="x", canonical_name="B")
        gs.upsert_edge(self.conn, src=a, dst=b, rel_type="relates_to", confidence=0.4, source="graphify", provenance=["m1.md"])
        gs.upsert_edge(self.conn, src=a, dst=b, rel_type="relates_to", confidence=0.9, source="graphify", provenance=["m2.md"])
        row = self.conn.execute("SELECT confidence, provenance FROM edges").fetchone()
        self.assertEqual(row["confidence"], 0.9)
        self.assertEqual(set(__import__("json").loads(row["provenance"])), {"m1.md", "m2.md"})

    def test_source_precedence_upgrades_to_deterministic(self):
        a = gs.upsert_node(self.conn, type="x", canonical_name="A")
        b = gs.upsert_node(self.conn, type="x", canonical_name="B")
        gs.upsert_edge(self.conn, src=a, dst=b, rel_type="works_at", confidence=0.5, source="graphify", provenance=["m1.md"])
        gs.upsert_edge(self.conn, src=a, dst=b, rel_type="works_at", confidence=1.0, source="deterministic", provenance=["m1.md"])
        row = self.conn.execute("SELECT source FROM edges").fetchone()
        self.assertEqual(row["source"], "deterministic")

    def test_forget_path_deletes_zombie_edge_but_keeps_shared_node(self):
        a = gs.upsert_node(self.conn, type="x", canonical_name="A", provenance=["m1.md", "m2.md"])
        b = gs.upsert_node(self.conn, type="x", canonical_name="B", provenance=["m1.md", "m2.md"])
        gs.upsert_edge(self.conn, src=a, dst=b, rel_type="relates_to", confidence=1.0, source="deterministic", provenance=["m1.md"])
        gs.forget_path(self.conn, "m1.md")
        self.assertIsNotNone(gs.resolve_node(self.conn, "A"))
        self.assertEqual(gs.neighbors(self.conn, a, depth=1), set())


if __name__ == "__main__":
    unittest.main()
