import importlib, json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = mock.patch.dict(os.environ, {"DECKHAND_LIBRARY": self.tmp.name})
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

    def test_legacy_env_still_honored(self):
        with mock.patch.dict(os.environ, {"EXPERT_BUILD_LIBRARY": self.tmp.name + "-legacy"}, clear=False):
            os.environ.pop("DECKHAND_LIBRARY", None)
            lib = importlib.reload(importlib.import_module("library"))
            self.assertEqual(lib.store_root(), Path(self.tmp.name + "-legacy"))

    def test_strict_reject_preserves_existing_item(self):
        self.lib.cmd_add(self.lib.parse_args(["add", "--name", "zz", "--file", str(self.src)]))
        hexfile = Path(self.tmp.name) / "bad.tsx"
        hexfile.write_text("export const C = () => <div style={{color:'#ff0000'}}/>;\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.lib.cmd_add(self.lib.parse_args(
                ["add", "--name", "zz", "--file", str(hexfile), "--force", "--strict"]))
        idx = [json.loads(l) for l in (Path(self.tmp.name) / "index.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        row = next(r for r in idx if r["name"] == "zz")
        for rel in row["files"]:
            self.assertTrue((Path(self.tmp.name) / rel).exists(), f"stale index points at missing {rel}")

    def test_duplicate_basenames_rejected(self):
        d1 = Path(self.tmp.name) / "a"; d1.mkdir()
        d2 = Path(self.tmp.name) / "b"; d2.mkdir()
        f1 = d1 / "card.tsx"; f1.write_text("export const A = () => null;\n", encoding="utf-8")
        f2 = d2 / "card.tsx"; f2.write_text("export const B = () => null;\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.lib.cmd_add(self.lib.parse_args(["add", "--name", "dup", "--file", str(f1), "--file", str(f2)]))

    def test_copy_creates_missing_target(self):
        fixture = ROOT / "tests" / "fixtures" / "pricing-card.tsx"
        self.lib.cmd_add(self.lib.parse_args(["add", "--name", "fx", "--file", str(fixture)]))
        dest = Path(self.tmp.name) / "proj" / "ui"      # does not exist yet
        self.lib.cmd_copy(self.lib.parse_args(["copy", "fx", "--to", str(dest)]))
        self.assertTrue((dest / "pricing-card.tsx").exists())


    def test_copy_force_guard_and_verify(self):
        self.lib.cmd_add(self.lib.parse_args(["add", "--name", "zz", "--file", str(self.src), "--source", "t"]))
        dest = Path(self.tmp.name) / "proj"; dest.mkdir()
        self.lib.cmd_copy(self.lib.parse_args(["copy", "zz", "--to", str(dest)]))
        with self.assertRaises(SystemExit):
            self.lib.cmd_copy(self.lib.parse_args(["copy", "zz", "--to", str(dest)]))
        self.lib.cmd_copy(self.lib.parse_args(["copy", "zz", "--to", str(dest), "--force"]))
        self.assertEqual(self.lib.cmd_verify(self.lib.parse_args(["verify"])), 0)
        import shutil as _s
        _s.rmtree(Path(self.tmp.name) / "items" / "zz")
        self.assertEqual(self.lib.cmd_verify(self.lib.parse_args(["verify"])), 1)

    def test_strict_requires_source_and_fonts(self):
        no_src = Path(self.tmp.name) / "plain.tsx"
        no_src.write_text("export const A = () => null;\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.lib.cmd_add(self.lib.parse_args(["add", "--name", "aa", "--file", str(no_src), "--strict"]))
        font = Path(self.tmp.name) / "fonted.tsx"
        font.write_text('export const B = () => <div style={{fontFamily: "Inter"}}/>;\n', encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.lib.cmd_add(self.lib.parse_args(["add", "--name", "bb", "--file", str(font), "--source", "t", "--strict"]))

    def test_add_rejects_directories_and_where_prints(self):
        with self.assertRaises(SystemExit):
            self.lib.cmd_add(self.lib.parse_args(["add", "--name", "cc", "--file", self.tmp.name, "--source", "t"]))
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.lib.cmd_where(self.lib.parse_args(["where"]))
        self.assertIn(self.tmp.name, buf.getvalue())

if __name__ == "__main__":
    unittest.main()
