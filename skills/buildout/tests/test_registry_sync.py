import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_sync as rs  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "registries.sample.json"

ALLOW = {"registries": [
    {"name": "@good", "homepage": "https://good2.example", "url": "https://good.example/r/{style}/{name}.json",
     "license": "MIT", "licenseEvidence": "test", "verifiedAt": "2026-01-01", "tags": ["t3"]},
    {"name": "@observing", "homepage": "https://obs.example", "url": "https://obs.example/r/{name}.json",
     "license": "MIT", "licenseEvidence": "test", "tags": ["t1"]},
    {"name": "@default", "homepage": "https://default.example", "url": None,
     "catalogUrl": "https://default.example/r/index.json",
     "license": "MIT", "licenseEvidence": "test", "tags": ["t4"]},
    {"name": "@plugin-only", "homepage": "https://plugin.example", "url": None,
     "license": "MIT", "licenseEvidence": "test", "tags": ["t2"], "integration": "tailwind-plugin"},
]}

class RegistrySyncTests(unittest.TestCase):
    def _entries(self, min_score=85):
        directory = json.loads(FIXTURE.read_text(encoding="utf-8"))
        kept = [c for c in (rs.compact_entry(e, min_score) for e in directory) if c]
        return rs.merge_allowlist(kept, ALLOW)

    def test_filter_hidden_degraded_low(self):
        names = {e["name"] for e in self._entries()}
        self.assertIn("@good", names)
        self.assertNotIn("@hidden", names)
        self.assertNotIn("@degraded", names)
        self.assertNotIn("@low", names)

    def test_allowlist_overrides_filter_and_synthesizes(self):
        entries = {e["name"]: e for e in self._entries()}
        self.assertIn("@observing", entries)                  # allowlisted despite status=observing
        self.assertTrue(entries["@observing"]["inAllowlist"])
        self.assertEqual(entries["@observing"]["license"], "MIT")
        self.assertIn("@plugin-only", entries)                # allowlist-only entry is synthesized
        self.assertFalse(entries["@plugin-only"].get("score"))

    def test_snapshot_shape_and_trim(self):
        e = {x["name"]: x for x in self._entries()}["@good"]
        self.assertLessEqual(len(e["description"]), 160)
        for k in ("name", "url", "homepage", "score", "inAllowlist", "integration"):
            self.assertIn(k, e)

    def test_allowlist_url_overrides_directory_url(self):
        entries = {e["name"]: e for e in self._entries()}
        self.assertEqual(entries["@good"]["url"], "https://good.example/r/{style}/{name}.json")
        self.assertEqual(entries["@good"]["homepage"], "https://good2.example")
        self.assertEqual(entries["@good"]["verifiedAt"], "2026-01-01")

    def test_allowlist_null_url_forces_bare_names(self):
        entries = {e["name"]: e for e in self._entries()}
        self.assertIsNone(entries["@default"]["url"])
        self.assertEqual(rs.render_install(entries["@default"]["url"], "button", rs.DEFAULT_STYLE),
                         "npx shadcn@latest add button")

    def test_render_install_and_default_style(self):
        self.assertEqual(rs.DEFAULT_STYLE, "base-nova")
        self.assertEqual(rs.render_install("https://reui.io/r/{style}/{name}.json", "c-alert-1", rs.DEFAULT_STYLE),
                         "npx shadcn@latest add https://reui.io/r/base-nova/c-alert-1.json")
        self.assertEqual(rs.render_install("https://diceui.com/r/{name}.json", "kanban", rs.DEFAULT_STYLE),
                         "npx shadcn@latest add https://diceui.com/r/kanban.json")
        self.assertEqual(rs.render_install(None, "button", rs.DEFAULT_STYLE),
                         "npx shadcn@latest add button")

    def test_classify_samples(self):
        self.assertEqual(rs.classify_samples([200, 401, 404]), "ok")      # any 200 wins (mixed free/pro)
        self.assertEqual(rs.classify_samples([404, 404]), "dead")
        self.assertEqual(rs.classify_samples([401, 403]), "gated")
        self.assertEqual(rs.classify_samples([429, 429]), "rate-limited")
        self.assertEqual(rs.classify_samples(["ERR:URLError"]), "error")
        self.assertEqual(rs.classify_samples([None, None]), "bare")
        self.assertEqual(rs.classify_samples([]), "unverified")

    def test_sample_indices_and_install_target(self):
        self.assertEqual(rs.sample_indices(5), [0, 1, 2, 3, 4])
        self.assertEqual(rs.sample_indices(1773), [0, 443, 886, 1329, 1772])
        self.assertEqual(rs.sample_indices(0), [])
        self.assertEqual(rs.install_target("npx shadcn@latest add https://x/r/a.json"), "https://x/r/a.json")
        self.assertIsNone(rs.install_target("npx shadcn@latest add button"))

    def test_catalog_items_and_catalog_url_override(self):
        self.assertEqual(rs.catalog_items({"items": [1, 2]}), [1, 2])
        self.assertEqual(rs.catalog_items([1, 2]), [1, 2])                # shadcn /r/index.json is a bare list
        self.assertEqual(rs.catalog_items(None), [])
        entries = {e["name"]: e for e in self._entries()}
        self.assertEqual(entries["@default"]["catalogUrl"], "https://default.example/r/index.json")

if __name__ == "__main__":
    unittest.main()
