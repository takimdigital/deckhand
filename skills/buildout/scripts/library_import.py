#!/usr/bin/env python3
"""library_import — put the owner's OWN saved components into the try-on catalog (source: 'mine').

Reads the component-library store (index.jsonl) and upserts one registry_items row per item, so
saved components appear in /catalog next to the measured pool — ranked first, still under the same
base filter. A row is only offered when the item carries what the catalog needs to be honest about:
  * a base (radix | base-ui | aria | none) recorded at save time,
  * a slot, and
  * a recorded licence (an item without one is skipped and counted — a licence that is not written
    down cannot be honoured; the item is still findable with `library.py find`).

    py scripts/library_import.py [--store PATH] [--db PATH] [--dry-run] [--prune]

By default the rows go to <store>/catalog-mine.db — the owner's own DB beside the store, joined to
the shipped data/templates.db read-only at query time. `--db <path>` still writes wherever it is
told (tests and migrations rely on it); nothing ever writes personal rows into the shipped DB.

--prune removes 'mine' rows whose item is no longer in the store (remove() archives items, so a
deleted component must stop being offered). Idempotent: re-run after any save; it never touches
rows from the measured pool.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import templates_db as DB  # noqa: E402
from templates_db import store_root  # noqa: E402  # moved to templates_db; re-exported for callers

BASE_VALUES = {"radix", "base-ui", "aria", "none"}


def read_index(store: Path) -> list[dict]:
    idx = store / "index.jsonl"
    if not idx.exists():
        return []
    rows = []
    for line in idx.read_text(encoding="utf-8").splitlines():
        if line.strip():
            try:
                rows.append(json.loads(line))
            except Exception:
                pass
    return rows


def offerable(row: dict) -> str | None:
    """None when the item can be offered; otherwise the plain reason it cannot."""
    base = (row.get("base") or "").strip()
    slot = (row.get("slot") or "").strip()
    lic = (row.get("license") or "").strip()
    if row.get("name") is None:
        return "row has no name"
    if base not in BASE_VALUES or not slot:
        return "no base/slot recorded (re-save from try-on, or `library.py add --base --slot`)"
    if not lic or lic == "unknown":
        return "no licence recorded (`library.py add --license ... --source-url ...`)"
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="import the personal component store into the try-on catalog")
    ap.add_argument("--store", default="", help="store root (default: $DECKHAND_LIBRARY / ~/deckhand-library)")
    ap.add_argument("--db", default=str(DB.mine_db()),
                    help="where the 'mine' rows are written (default: <store>/catalog-mine.db)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--prune", action="store_true", help="also remove 'mine' rows whose item left the store")
    args = ap.parse_args(argv)

    store = store_root(args.store or None)
    if not (store / "index.jsonl").exists():
        print(json.dumps({"ok": False, "reason": "STORE_NOT_FOUND", "store": str(store),
                          "hint": "the store is created by its first `library.py add`"}, ensure_ascii=False, indent=1))
        return 1
    rows = read_index(store)
    imported, skipped = [], []
    for r in rows:
        why = offerable(r)
        if why:
            skipped.append({"item": r.get("name"), "why": why})
            continue
        imported.append({
            "registry": "mine", "item": r["name"], "style": "",
            "type": "registry:component", "title": r["name"],
            "description": (r.get("source") or "")[:160],
            "categories": json.dumps(r.get("tags", []), ensure_ascii=False),
            "slot": r["slot"], "slot_kind": "",
            "base": r["base"],
            "deps": json.dumps(r.get("deps", []), ensure_ascii=False),
            # aliased imports live in the item's meta - an unknown @scope/name in registryDependencies
            # is a hard install error in the shadcn CLI, so nothing is invented here
            "registry_deps": json.dumps([]),
            "item_url": r.get("sourceUrl") or "", "index_url": "",
            "free": 1, "license": r["license"], "license_evidence": r.get("licenseEvidence") or "",
            "content_sha": "", "fetched_at": DB.now(), "updated_at": DB.now(),
        })

    con = DB.connect(Path(args.db))
    pruned = []
    if args.prune:
        names = {r.get("name") for r in rows}
        cur = [c["item"] for c in con.execute("SELECT item FROM registry_items WHERE registry = 'mine'").fetchall()]
        pruned = [it for it in cur if it not in names]
        if not args.dry_run:
            for it in pruned:
                con.execute("DELETE FROM registry_items WHERE registry = 'mine' AND item = ?", (it,))
            con.commit()
    written = 0
    if not args.dry_run:
        for rec in imported:
            DB.reg_upsert(con, rec)
            written += 1

    out = {"ok": True, "store": str(store), "db": str(args.db), "dry_run": args.dry_run,
           "items_in_store": len(rows), "offered": len(imported), "written": written,
           "pruned": len(pruned), "skipped": skipped}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
