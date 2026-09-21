import sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import assemble_pick as ap  # noqa: E402

def it(id_, section, tags, registry="@a", themeable=True, size=None):
    d = {"id": id_, "name": id_.split("/")[-1], "registry": registry,
         "section": section, "tags": tags, "themeable": themeable, "install": f"npx shadcn@latest add {id_}"}
    if size is not None:
        d["size_kb"] = size
    return d

POOL = [
    it("@a/hero-one", ["hero"], ["animated"], "@a"),
    it("@b/hero-two", ["hero"], ["animated", "glow"], "@b"),
    it("@c/hero-three", ["hero"], [], "@c"),
    it("@d/pricing", ["pricing"], ["cards"], "@d"),
    it("@e/unthemed", ["hero"], ["animated"], "@e", themeable=False),
]

class PickTests(unittest.TestCase):
    def test_same_seed_same_result(self):
        r1 = ap.pick(POOL, "hero", ["animated"], k=2, seed=4242)
        r2 = ap.pick(POOL, "hero", ["animated"], k=2, seed=4242)
        self.assertEqual(r1, r2)
        self.assertEqual(len(r1), 2)

    def test_filters_section_and_unthemed(self):
        got = {p["id"] for p in ap.pick(POOL, "hero", [], k=5, seed=1)}
        self.assertNotIn("@d/pricing", got)      # wrong section
        self.assertNotIn("@e/unthemed", got)     # not themeable

    def test_allow_unthemed_flag(self):
        got = {p["id"] for p in ap.pick(POOL, "hero", [], k=5, seed=1, allow_unthemed=True)}
        self.assertIn("@e/unthemed", got)

    def test_k_never_exceeds_pool(self):
        got = ap.pick(POOL, "hero", [], k=99, seed=3)
        self.assertLessEqual(len(got), 3)

    def test_empty_pool_signal(self):
        self.assertEqual(ap.pick([], "hero", [], k=3, seed=1), [])

    def test_missing_glob_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            ap.load_items([str(ROOT / "data" / "items" / "definitely-not-there-*.jsonl")])

    def test_uncurated_items_need_text_match(self):
        pool = POOL + [it("@f/mystery", [], [], "@f"), it("@g/animated-hero-widget", [], ["animated"], "@g")]
        got = {p["id"] for p in ap.pick(pool, "hero", ["animated"], k=99, seed=2)}
        self.assertNotIn("@f/mystery", got)              # no section, no text match
        self.assertIn("@g/animated-hero-widget", got)    # no section but name matches

if __name__ == "__main__":
    unittest.main()
