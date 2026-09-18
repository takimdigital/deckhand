import importlib, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"EXPERT_BUILD_LIBRARY": self.tmp.name})
        self.env.start()
        self.lib = importlib.reload(importlib.import_module("library"))
        self.src = Path(self.tmp.name) / "pricing-card.tsx"
        self.src.write_text('import { Card } from "@/components/ui/card";\nimport { motion } from "motion/react";\nexport const C = () => null;\n', encoding="utf-8")

    def tearDown(self):
        self.env.stop(); self.tmp.cleanup()

    def test_add_then_find(self):
        self.lib.cmd_add(self.lib.parse_args(["add", "--name", "pricing-card", "--file", str(self.src), "--tags", "pricing,cards", "--section", "pricing"]))
        idx = (Path(self.tmp.name) / "index.jsonl").read_text(encoding="utf-8")
        self.assertIn("pricing-card", idx)
        self.assertIn("motion", idx)          # dep extracted; "@/..." alias ignored
        hits = self.lib.search("pricing")
        self.assertEqual(hits[0]["name"], "pricing-card")

    def test_dedupe_requires_force(self):
        self.lib.cmd_add(self.lib.parse_args(["add", "--name", "zz", "--file", str(self.src)]))
        with self.assertRaises(SystemExit):
            self.lib.cmd_add(self.lib.parse_args(["add", "--name", "zz", "--file", str(self.src)]))

    def test_copy_to_project(self):
        self.lib.cmd_add(self.lib.parse_args(["add", "--name", "zz", "--file", str(self.src)]))
        dest = Path(self.tmp.name) / "proj"; dest.mkdir()
        self.lib.cmd_copy(self.lib.parse_args(["copy", "zz", "--to", str(dest)]))
        self.assertTrue((dest / "pricing-card.tsx").exists())

    def test_registry_json_rendered(self):
        self.lib.cmd_add(self.lib.parse_args(["add", "--name", "zz", "--file", str(self.src)]))
        reg = json.loads((Path(self.tmp.name) / "registry.json").read_text(encoding="utf-8"))
        self.assertEqual(reg["items"][0]["name"], "zz")

if __name__ == "__main__":
    unittest.main()
