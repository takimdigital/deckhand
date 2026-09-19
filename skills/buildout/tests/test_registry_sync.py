import json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import registry_sync as rs  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "registries.sample.json"

ALLOW = {"registries": [
    {"name": "@observing", "homepage": "https://obs.example", "url": "https://obs.example/r/{name}.json",
     "license": "MIT", "licenseEvidence": "test", "tags": ["t1"]},
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

if __name__ == "__main__":
    unittest.main()
