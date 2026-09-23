#!/usr/bin/env python3
"""templates.db — the Template Factory registry.

SQLite is the truth; data/templates.json is the agent-readable export.
Nothing enters as "verified" by hand: `template_intake.py` measures a repo
(license, stack, deps, boot) and writes the row. Scoring is deterministic.

usage (from the skill dir):
  py scripts/templates_db.py init [--seed data/templates.seed.json] [--force]
  py scripts/templates_db.py import <intake.json|intake.jsonl>
  py scripts/templates_db.py list [--status S] [--shape S] [--canonical] [--json]
  py scripts/templates_db.py score --intake <intake.json> [--top N] [--json]
  py scripts/templates_db.py export [--out data/templates.json]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sqlite3
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = SKILL_DIR / "data" / "templates.db"
DEFAULT_EXPORT = SKILL_DIR / "data" / "templates.json"

SHAPES = ("saas", "marketplace", "booking", "catalogue", "leadgen", "internal", "unknown")
STATUSES = ("unverified", "verified", "rejected")

# What the factory treats as the canonical lane (ref 10-match.md).
CANONICAL_FRAMEWORK = "next"
CANONICAL_AUTH = ("better-auth", "none", "custom")
CANONICAL_DB = ("postgres", "postgresql")

TPL_FIELDS = [
    "name", "url", "repo", "rank", "status", "reject_reason",
    "license_spdx", "license_file", "license_ok",
    "stars", "forks", "open_issues", "pushed_at", "archived", "default_branch", "size_kb",
    "shape", "shape_source", "stack", "canonical", "canonical_notes",
    "deps_vendor", "deps_selfhost", "deps_unclassified",
    "swap_map", "boot_install_ok", "boot_build_ok", "boot_start_ok", "boot_tests",
    "boot_ms", "boot_port", "rebrand_surface", "risk_flags", "evidence", "updated_at",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  url TEXT NOT NULL,
  repo TEXT,
  rank INTEGER,
  status TEXT NOT NULL DEFAULT 'unverified',
  reject_reason TEXT,
  license_spdx TEXT, license_file TEXT, license_ok INTEGER,
  stars INTEGER, forks INTEGER, open_issues INTEGER,
  pushed_at TEXT, archived INTEGER, default_branch TEXT, size_kb INTEGER,
  shape TEXT, shape_source TEXT, stack TEXT,
  canonical INTEGER, canonical_notes TEXT,
  deps_vendor TEXT, deps_selfhost TEXT, deps_unclassified TEXT,
  swap_map TEXT,
  boot_install_ok INTEGER, boot_build_ok INTEGER, boot_start_ok INTEGER,
  boot_tests TEXT, boot_ms INTEGER, boot_port INTEGER,
  rebrand_surface TEXT, risk_flags TEXT, evidence TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS intake_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template TEXT NOT NULL, run_at TEXT NOT NULL, upstream_commit TEXT, mode TEXT, log TEXT
);
"""


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def jload(v, default):
    if v in (None, ""):
        return default
    try:
        return json.loads(v)
    except Exception:
        return default


def compute_canonical(stack: dict) -> tuple[int, str]:
    fw = (stack or {}).get("framework") or "?"
    db = (stack or {}).get("db") or "?"
    auth = (stack or {}).get("auth") or "?"
    docker = bool((stack or {}).get("docker"))
    notes = []
    ok = True
    if fw != CANONICAL_FRAMEWORK:
        ok = False
        notes.append(f"framework={fw} (canonical: {CANONICAL_FRAMEWORK})")
    if db not in CANONICAL_DB:
        ok = False
        notes.append(f"db={db} (canonical: postgres)")
    if auth not in CANONICAL_AUTH:
        ok = False
        notes.append(f"auth={auth} -> needs swap to better-auth")
    if not docker:
        notes.append("no docker/compose (deploy target: Coolify wants a Dockerfile or nixpacks)")
    return (1 if ok else 0), "; ".join(notes)


def upsert(con: sqlite3.Connection, rec: dict) -> None:
    rec = {k: rec.get(k) for k in TPL_FIELDS if k in rec} | {
        k: rec[k] for k in ("name", "url") if k in rec
    }
    # normalise json-ish fields
    for f in ("stack", "deps_vendor", "deps_selfhost", "deps_unclassified", "swap_map",
              "rebrand_surface", "risk_flags", "evidence"):
        if isinstance(rec.get(f), (dict, list)):
            rec[f] = json.dumps(rec[f], ensure_ascii=False)
    stack = jload(rec.get("stack"), {})
    if stack and "canonical" not in rec:
        rec["canonical"], rec["canonical_notes"] = compute_canonical(stack)
    rec["updated_at"] = now()
    cols = [c for c in TPL_FIELDS if c in rec]
    existing = con.execute("SELECT id FROM templates WHERE name = ?", (rec.get("name"),)).fetchone()
    if existing:
        sets = ", ".join(f"{c} = ?" for c in cols)
        con.execute(f"UPDATE templates SET {sets} WHERE name = ?", [rec[c] for c in cols] + [rec["name"]])
    else:
        con.execute(f"INSERT INTO templates ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                    [rec[c] for c in cols])
    con.commit()


def load_seed(path: Path) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = data.get("templates", data if isinstance(data, list) else [])
    out = []
    for t in rows:
        url = t.get("url") or ""
        repo = url.rstrip("/").split("github.com/", 1)[-1] if "github.com/" in url else t.get("repo")
        out.append({
            "name": t.get("name") or (repo or "?").split("/")[-1],
            "url": url, "repo": repo, "rank": t.get("rank"),
            "status": t.get("status", "unverified"),
            "risk_flags": [t["user_note"]] if t.get("user_note") else [],
            "evidence": {"source": "seed", "added_at": now()},
        })
    return out


def rowdict(r: sqlite3.Row) -> dict:
    d = dict(r)
    for f in ("stack", "deps_vendor", "deps_selfhost", "deps_unclassified", "swap_map",
              "rebrand_surface", "risk_flags", "evidence"):
        d[f] = jload(d.get(f), None)
    return d


# ---------------------------------------------------------------- matching
def score_template(intake: dict, row: dict) -> tuple[int, list[str], list[str]]:
    """Deterministic score. Returns (score, reasons, blockers)."""
    s = 0
    reasons: list[str] = []
    reasons_pre: list[str] = []
    blockers: list[str] = []
    if row.get("status") == "rejected" or not row.get("license_ok"):
        blockers.append("license not verified MIT/Apache (or rejected)")
        return -1, reasons, blockers
    if row.get("archived"):
        blockers.append("repo archived upstream")
    flags = [f for f in (row.get("risk_flags") or []) if isinstance(f, dict)]
    needs_vendor_keys = any(f.get("kind") == "vendor-keys-required" for f in flags)
    if row.get("boot_build_ok") == 0 and not needs_vendor_keys:
        blockers.append("boot: build failed on record")
    elif row.get("boot_build_ok") == 0 and needs_vendor_keys:
        reasons_pre.append("build needs vendor keys — swap first (not a pool rejection)")

    want_shape = (intake.get("shape") or "").lower()
    if want_shape and row.get("shape") == want_shape:
        s += 40
        reasons.append(f"shape match ({want_shape})")
    elif want_shape and row.get("shape") in ("unknown", None, ""):
        reasons.append("shape heuristic found no signal — classify it (import with shape + shape_source=manual)")
    else:
        reasons.append(f"shape differs (wants {want_shape}, is {row.get('shape')})")

    stack = row.get("stack") or {}
    caps = set()
    vendor = {str(v).lower() for v in (row.get("deps_vendor") or [])}
    if stack.get("auth") not in (None, "", "none"):
        caps.add("accounts")
    if stack.get("i18n"):
        caps.add("i18n")
    if stack.get("jobs"):
        caps.add("jobs")
    if stack.get("admin"):
        caps.add("admin")
    if stack.get("tests"):
        caps.add("tests")
    if vendor & {"stripe", "lemonsqueezy", "polar", "paddle"}:
        caps.add("payments")
    if stack.get("db"):
        caps.add("database")
    feats = {str(f).lower() for f in (intake.get("features") or [])}
    hit = sorted(feats & caps)
    s += min(len(hit) * 10, 30)
    if hit:
        reasons.append("features: " + ", ".join(hit))
    missing = sorted(feats - caps)
    if missing:
        reasons.append("not in stack: " + ", ".join(missing))

    langs = [str(x).lower() for x in (intake.get("languages") or [])]
    rtl = any(x in ("ar", "he", "fa", "ur") for x in langs)
    if rtl:
        if stack.get("i18n") and stack.get("rtl"):
            s += 10
            reasons.append("RTL + i18n present")
        elif stack.get("i18n"):
            s += 4
            reasons.append("i18n present, RTL support unproven")
        else:
            reasons.append("RTL requested, no i18n found")

    if row.get("canonical"):
        s += 15
        reasons.append("canonical stack")
    else:
        notes = row.get("canonical_notes") or ""
        if notes:
            reasons.append("non-canonical: " + notes)

    if row.get("boot_start_ok"):
        s += 10
        reasons.append("boots measured green")
    elif row.get("boot_build_ok"):
        s += 5
        reasons.append("build green, start unmeasured")

    if row.get("status") == "verified":
        s += 5
        reasons.append("intake verified")

    # community proof: a repo nobody uses is not production-ready
    stars = row.get("stars") or 0
    if stars >= 1000:
        s += 5
        reasons.append(f"community: {stars}★")
    elif stars >= 200:
        s += 2
        reasons.append(f"community: {stars}★")
    elif stars < 10:
        s -= 10
        reasons.append(f"penalty: {stars}★ (unproven)")

    # swap cost is real work: each vendor dep needs a proven adapter
    swaps = len(vendor)
    if swaps:
        s -= min(swaps * 2, 10)
        reasons.append(f"swap cost: {swaps} vendor dep(s) -> -{min(swaps * 2, 10)}")

    for f in (row.get("risk_flags") or []):
        if isinstance(f, dict):
            if f.get("kind") == "stale":
                s -= 20
                reasons.append("penalty: stale upstream")
            elif f.get("kind") == "no-tests":
                s -= 5
                reasons.append("penalty: no tests detected")
            else:
                reasons.append(f"risk: {f.get('kind')}")
        else:
            reasons.append(f"note: {f}")
    return s, reasons_pre + reasons, blockers


def cmd_score(con, intake_path: Path, top: int, as_json: bool) -> int:
    intake = json.loads(Path(intake_path).read_text(encoding="utf-8"))
    rows = [rowdict(r) for r in con.execute("SELECT * FROM templates").fetchall()]
    scored = []
    for r in rows:
        s, reasons, blockers = score_template(intake, r)
        scored.append({"name": r["name"], "url": r["url"], "score": s,
                       "reasons": reasons, "blockers": blockers, "row": r})
    scored.sort(key=lambda x: (-x["score"], x["name"]))
    # `> 0`, not `>= 0`: a row with nothing in its favour is not a candidate (10-match.md).
    ok = [x for x in scored if not x["blockers"] and x["score"] > 0]
    out = ok[:top] if top else ok
    if as_json:
        print(json.dumps({"intake": intake, "ranked": out,
                          "blocked": [x for x in scored if x["blockers"]]}, ensure_ascii=False, indent=2))
    else:
        print(f"intake: shape={intake.get('shape')} features={intake.get('features')} "
              f"languages={intake.get('languages')} hosting={intake.get('hosting')}")
        print(f"candidates: {len(rows)} | eligible: {len(ok)}\n")
        for i, x in enumerate(out, 1):
            print(f"{i}. {x['name']}  score={x['score']}  {x['url']}")
            # print EVERY reason — the swap cost and "not in stack" lines land past index 6 and are
            # exactly what the owner needs to choose; silently cutting them hides the cost of a pick.
            for r in x["reasons"][:12]:
                print(f"     - {r}")
        if not out:
            print("nothing ranks above 0 — there is no honest match in this pool for this ask.\n"
                  "  Say so plainly (do not rank a bad candidate): grow the pool with\n"
                  "  `py scripts/template_intake.py --repo <owner/name>`, or change the ask with the owner.")
        blocked = [x for x in scored if x["blockers"]]
        if blocked:
            print("\nblocked:")
            for x in blocked:
                print(f"  {x['name']}: {'; '.join(x['blockers'])}")
    return 0 if out else 2


def cmd_list(con, args) -> int:
    q = "SELECT * FROM templates WHERE 1=1"
    p: list = []
    if args.status:
        q += " AND status = ?"; p.append(args.status)
    if args.shape:
        q += " AND shape = ?"; p.append(args.shape)
    if args.canonical:
        q += " AND canonical = 1"
    rows = [rowdict(r) for r in con.execute(q + " ORDER BY COALESCE(rank, 999), name", p).fetchall()]
    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0
    print(f"{'name':28} {'status':10} {'lic':4} {'★':>6} {'shape':11} {'stack':28} {'can':3} boot")
    for r in rows:
        st = r.get("stack") or {}
        stack_s = f"{(st.get('framework') or '?')}/{(st.get('db') or '?')}/{(st.get('auth') or '?')}"
        boot = "".join(["-" if r.get("boot_install_ok") is None else ("i" if r["boot_install_ok"] else "I"),
                        "-" if r.get("boot_build_ok") is None else ("b" if r["boot_build_ok"] else "B"),
                        "-" if r.get("boot_start_ok") is None else ("s" if r["boot_start_ok"] else "S")])
        print(f"{r['name'][:27]:28} {r.get('status','')[:9]:10} {(r.get('license_spdx') or '?')[:3]:4} "
              f"{(r.get('stars') or 0):>6} {(r.get('shape') or '?')[:10]:11} {stack_s[:27]:28} "
              f"{r.get('canonical') or 0:<3} {boot}")
    print(f"\n{len(rows)} template(s). boot legend: i/b/s = install/build/start ok, uppercase = failed, '-' = not measured")
    return 0


def cmd_export(con, out: Path) -> int:
    rows = [rowdict(r) for r in con.execute("SELECT * FROM templates ORDER BY COALESCE(rank, 999), name").fetchall()]
    payload = {"generated_at": now(), "source": "data/templates.db", "count": len(rows), "templates": rows}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"exported {len(rows)} template(s) -> {out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Template Factory registry (SQLite truth + JSON export)")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("--seed", default=str(SKILL_DIR / "data" / "templates.seed.json")); p.add_argument("--force", action="store_true")
    p = sub.add_parser("import"); p.add_argument("path")
    p = sub.add_parser("list"); p.add_argument("--status", choices=STATUSES); p.add_argument("--shape", choices=SHAPES); p.add_argument("--canonical", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("score"); p.add_argument("--intake", required=True); p.add_argument("--top", type=int, default=3); p.add_argument("--json", action="store_true")
    p = sub.add_parser("export"); p.add_argument("--out", default=str(DEFAULT_EXPORT))
    args = ap.parse_args(argv)

    db = Path(args.db)
    if args.cmd == "init" and args.force and db.exists():
        db.unlink()
    con = connect(db)

    if args.cmd == "init":
        seed = Path(args.seed)
        if seed.exists():
            rows = load_seed(seed)
            for r in rows:
                upsert(con, r)
            print(f"init: {len(rows)} seed record(s) -> {db}")
        else:
            print(f"init: schema only (no seed at {seed}) -> {db}")
        return 0
    if args.cmd == "import":
        path = Path(args.path)
        recs = []
        if path.suffix == ".jsonl":
            recs = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        else:
            data = json.loads(path.read_text(encoding="utf-8"))
            recs = data.get("templates", data if isinstance(data, list) else [data])
        for r in recs:
            upsert(con, r)
        print(f"imported {len(recs)} record(s) into {db}")
        return 0
    if args.cmd == "list":
        return cmd_list(con, args)
    if args.cmd == "score":
        return cmd_score(con, Path(args.intake), args.top, args.json)
    if args.cmd == "export":
        return cmd_export(con, Path(args.out))
    return 1


if __name__ == "__main__":
    sys.exit(main())
