import os, tempfile, unittest, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
import wire
import graph_store as gs


class WireTest(unittest.TestCase):
    def test_entities_from_wikilinks(self):
        self.assertEqual(wire.extract_entities("[[Bob]] works at [[Acme AI]]."), ["Bob", "Acme AI"])

    def test_entities_from_backticks_single_token(self):
        ents = wire.extract_entities("the stack uses `httpx` and `ruff` today")
        self.assertIn("httpx", ents)
        self.assertIn("ruff", ents)

    def test_entities_from_known_dictionary_bare_mention(self):
        ents = wire.extract_entities("cool-ui is the org design system", known={"cool-ui"})
        self.assertIn("cool-ui", ents)

    def test_multi_word_backtick_is_not_an_entity(self):
        self.assertEqual(wire.extract_entities("run `git rebase main` first"), [])

    def test_edge_canonical_engineering(self):
        edges = wire.extract_edges("`httpx` is the standard for `webshop`")
        self.assertIn(("httpx", "standard_for", "webshop"), edges)

    def test_edge_canonical_business(self):
        self.assertIn(("Acme", "acquired", "Globex"),
                      wire.extract_edges("[[Acme]] acquired [[Globex]]."))

    def test_edge_open_vocab_kept_verbatim(self):
        self.assertIn(("Bob", "mentors", "Carol"),
                      wire.extract_edges("[[Bob]] mentors [[Carol]]."))

    def test_edge_subject_anchored_no_spurious_object_edge(self):
        edges = wire.extract_edges("[[Carol]] founded [[Initech]] and advises [[Globex]].")
        self.assertIn(("Carol", "founded", "Initech"), edges)
        self.assertIn(("Carol", "advises", "Globex"), edges)
        self.assertNotIn(("Initech", "advises", "Globex"), edges)

    def test_edge_relates_to_when_connector_is_stopwords(self):
        self.assertIn(("Bob", "relates_to", "Carol"),
                      wire.extract_edges("[[Bob]] and [[Carol]]."))

    def test_wire_file_persists_and_dictionary_grows(self):
        d = tempfile.mkdtemp()
        conn = gs.connect(os.path.join(d, "graph.sqlite"))
        p1 = os.path.join(d, "m1.md")
        open(p1, "w").write("[[Bob]] works at [[Acme AI]].\n")
        wire.wire_file(conn, p1)
        self.assertIsNotNone(gs.resolve_node(conn, "Acme AI"))
        p2 = os.path.join(d, "m2.md")
        open(p2, "w").write("Bob founded Acme AI.\n")
        wire.wire_file(conn, p2)
        bob = gs.resolve_node(conn, "Bob")
        self.assertIn(("Bob", "founded", "Acme AI"),
                      [(gs_row_name(conn, s), r, gs_row_name(conn, dd))
                       for s, dd, r in _edges(conn)])

    def test_wire_file_idempotent(self):
        d = tempfile.mkdtemp()
        conn = gs.connect(os.path.join(d, "graph.sqlite"))
        p = os.path.join(d, "m1.md")
        open(p, "w").write("[[Bob]] works at [[Acme AI]].\n")
        wire.wire_file(conn, p)
        wire.wire_file(conn, p)
        self.assertEqual(conn.execute("SELECT COUNT(*) c FROM edges").fetchone()["c"], 1)


def _edges(conn):
    return [(r["src"], r["dst"], r["rel_type"]) for r in conn.execute("SELECT src, dst, rel_type FROM edges")]


def gs_row_name(conn, nid):
    return conn.execute("SELECT canonical_name FROM nodes WHERE id=?", (nid,)).fetchone()["canonical_name"]


if __name__ == "__main__":
    unittest.main()
