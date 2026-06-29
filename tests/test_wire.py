import os, tempfile, unittest, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
import wire
import graph_store as gs


class WireTest(unittest.TestCase):
    def test_extract_entities_reads_wikilinks(self):
        ents = wire.extract_entities("[[Bob]] works at [[Acme AI]].")
        self.assertEqual(ents, ["Bob", "Acme AI"])

    def test_extract_edges_single_cue(self):
        edges = wire.extract_edges("[[Bob]] works at [[Acme AI]].")
        self.assertIn(("Bob", "works_at", "Acme AI"), edges)

    def test_extract_edges_multiple_cues_in_sentence(self):
        edges = wire.extract_edges("[[Carol]] founded [[Initech]] and advises [[Globex]].")
        self.assertIn(("Carol", "founded", "Initech"), edges)
        self.assertIn(("Carol", "advises", "Globex"), edges)

    def test_extract_edges_unknown_cue_is_relates_to(self):
        edges = wire.extract_edges("[[Bob]] knows [[Carol]].")
        self.assertIn(("Bob", "relates_to", "Carol"), edges)

    def test_extract_edges_no_spurious_cross_object_edge(self):
        edges = wire.extract_edges("[[Carol]] founded [[Initech]] and advises [[Globex]].")
        self.assertNotIn(("Initech", "advises", "Globex"), edges)
        self.assertNotIn(("Initech", "relates_to", "Globex"), edges)

    def test_extract_edges_no_spurious_cross_object_relates_to(self):
        edges = wire.extract_edges("[[Alice]] knows [[Bob]] and also [[Carol]].")
        self.assertIn(("Alice", "relates_to", "Bob"), edges)
        self.assertIn(("Alice", "relates_to", "Carol"), edges)
        self.assertNotIn(("Bob", "relates_to", "Carol"), edges)

    def test_wire_file_persists_nodes_and_edges(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "m1.md")
        open(p, "w").write("---\nname: m1\n---\n[[Bob]] works at [[Acme AI]].\n")
        conn = gs.connect(os.path.join(d, "graph.sqlite"))
        wire.wire_file(conn, p)
        bob = gs.resolve_node(conn, "Bob")
        acme = gs.resolve_node(conn, "Acme AI")
        self.assertIsNotNone(bob)
        self.assertIn(acme, gs.neighbors(conn, bob, depth=1))

    def test_wire_file_is_idempotent(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "m1.md")
        open(p, "w").write("[[Bob]] works at [[Acme AI]].\n")
        conn = gs.connect(os.path.join(d, "graph.sqlite"))
        wire.wire_file(conn, p)
        wire.wire_file(conn, p)
        n = conn.execute("SELECT COUNT(*) c FROM edges").fetchone()["c"]
        self.assertEqual(n, 1)


if __name__ == "__main__":
    unittest.main()
