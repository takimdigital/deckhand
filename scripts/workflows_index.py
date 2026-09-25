#!/usr/bin/env python3
"""Build workflows/community/index.json from workflows/community/*.json — every file linted strictly (allow-listed
commands only, no private calls, no user paths, no secrets). `--check` fails when a file is invalid or the index is
stale (CI). The index is what `dh workflow query` reads: one row per workflow, the file fetched only when used."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "deckhand"))

from dhlib import workflow as WF  # noqa: E402

DIR = ROOT / "workflows" / "community"


def build() -> tuple[dict, list]:
    rows, problems = [], []
    ids = set()
    for p in sorted(DIR.glob("*.json")):
        if p.name == "index.json":
            continue
        try:
            wf = json.loads(p.read_text(encoding="utf-8"))
        except ValueError as e:
            problems.append(f"{p.name}: not JSON ({e})")
            continue
        lt = WF.lint(wf, strict=True)
        problems += [f"{p.name}: {e}" for e in lt["errors"]]
        if p.stem != wf.get("id"):
            problems.append(f"{p.name}: the file name must be <id>.json ({wf.get('id')}.json)")
        if wf.get("id") in ids:
            problems.append(f"{p.name}: duplicate id {wf.get('id')}")
        ids.add(wf.get("id"))
        if lt["ok"]:
            row = WF.row_of(wf, "community")
            row["file"] = p.name
            row["reviewed"] = bool((wf.get("proof") or {}).get("reviewed"))
            rows.append({k: v for k, v in row.items() if k != "source"})
    return {"schema": "deckhand.workflow-index/1", "workflows": rows}, problems


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    idx, problems = build()
    text = json.dumps(idx, indent=2, ensure_ascii=False) + "\n"
    target = DIR / "index.json"
    if "--check" in argv:
        stale = not target.exists() or target.read_text(encoding="utf-8") != text
        for p in problems:
            print("✗", p)
        if stale:
            print("✗ workflows/community/index.json is stale: run python3 scripts/workflows_index.py")
        print(f"{len(idx['workflows'])} community workflows, {len(problems)} problems")
        return 1 if problems or stale else 0
    if problems:
        for p in problems:
            print("✗", p)
        return 1
    target.write_text(text, encoding="utf-8")
    print(f"index: {len(idx['workflows'])} workflows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
