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
  py scripts/templates_db.py import-details <dir|file>   # pool-details contract: data/details/*.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
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
    # deep pool details (references/pool-details.md): a measured digest of the template
    "details", "details_at", "details_file", "features", "locales", "swap_burden",
]

# Registry items are keyed (registry, item, style): one registry may ship several style families
# with the SAME item name and DIFFERENT code (shadcn `base-nova` = Base UI, `new-york-v4` = Radix),
# and a project must only ever see the family that matches its own primitive base.
REGISTRY_ITEMS_DDL = """
CREATE TABLE IF NOT EXISTS registry_items (
  registry TEXT NOT NULL,
  item TEXT NOT NULL,
  style TEXT NOT NULL DEFAULT '',
  type TEXT, title TEXT, description TEXT,
  categories TEXT, slot TEXT, slot_kind TEXT,
  base TEXT, deps TEXT, registry_deps TEXT,
  item_url TEXT, index_url TEXT,
  free INTEGER, license TEXT, license_evidence TEXT,
  content_sha TEXT, fetched_at TEXT, updated_at TEXT,
  PRIMARY KEY (registry, item, style)
);
"""

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
  rebrand_surface TEXT, risk_flags TEXT, evidence TEXT, updated_at TEXT,
  details TEXT, details_at TEXT, details_file TEXT,
  features TEXT, locales TEXT, swap_burden TEXT
);
CREATE TABLE IF NOT EXISTS intake_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template TEXT NOT NULL, run_at TEXT NOT NULL, upstream_commit TEXT, mode TEXT, log TEXT
);
CREATE TABLE IF NOT EXISTS registry_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT NOT NULL, finished_at TEXT, style TEXT,
  registries TEXT, written INTEGER, skipped INTEGER
);
-- Component registry (try-on): normalized items from MIT shadcn-compatible registries.
-- Same philosophy as `templates`: measured remotely, license-gated, only a shortlist is ever read.
""" + REGISTRY_ITEMS_DDL + """
"""


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Columns added after the first row ever existed: `connect` migrates, so an older
# templates.db keeps working instead of needing a rebuild.
DETAIL_COLS = {"details": "TEXT", "details_at": "TEXT", "details_file": "TEXT",
               "features": "TEXT", "locales": "TEXT", "swap_burden": "TEXT"}

# Every column the registry ever adds, so an older templates.db is brought forward instead of crashing
# (`name`/`url` are NOT NULL and always first; they are never ALTER-ADDed).
COL_TYPES = {
    "repo": "TEXT", "rank": "INTEGER", "status": "TEXT", "reject_reason": "TEXT",
    "license_spdx": "TEXT", "license_file": "TEXT", "license_ok": "INTEGER",
    "stars": "INTEGER", "forks": "INTEGER", "open_issues": "INTEGER",
    "pushed_at": "TEXT", "archived": "INTEGER", "default_branch": "TEXT", "size_kb": "INTEGER",
    "shape": "TEXT", "shape_source": "TEXT", "stack": "TEXT",
    "canonical": "INTEGER", "canonical_notes": "TEXT",
    "deps_vendor": "TEXT", "deps_selfhost": "TEXT", "deps_unclassified": "TEXT", "swap_map": "TEXT",
    "boot_install_ok": "INTEGER", "boot_build_ok": "INTEGER", "boot_start_ok": "INTEGER",
    "boot_tests": "TEXT", "boot_ms": "INTEGER", "boot_port": "INTEGER",
    "rebrand_surface": "TEXT", "risk_flags": "TEXT", "evidence": "TEXT", "updated_at": "TEXT",
    **DETAIL_COLS,
}


def _migrate(con: sqlite3.Connection) -> list[str]:
    have = {r["name"] for r in con.execute("PRAGMA table_info(templates)")}
    added = []
    if not have:
        return added
    for col, typ in COL_TYPES.items():
        if col not in have:
            con.execute(f"ALTER TABLE templates ADD COLUMN {col} {typ}")
            added.append(col)
    if added:
        con.commit()
    return added


def _migrate_registry_items(con: sqlite3.Connection) -> bool:
    """registry_items gained `style` in its key. Rows written before it get their style from their
    own item_url (/styles/<style>/...) — an old shadcn row IS a base-nova row, and saying so is what
    keeps Base UI code out of a Radix project's candidate list."""
    cols = {r["name"] for r in con.execute("PRAGMA table_info(registry_items)")}
    if not cols or "style" in cols:
        return False
    old = [dict(r) for r in con.execute("SELECT * FROM registry_items")]
    con.execute("ALTER TABLE registry_items RENAME TO registry_items_old")
    con.executescript(REGISTRY_ITEMS_DDL)
    fields = ("registry", "item", "style", "type", "title", "description", "categories", "slot",
              "slot_kind", "base", "deps", "registry_deps", "item_url", "index_url", "free",
              "license", "license_evidence", "content_sha", "fetched_at", "updated_at")
    rows = []
    for r in old:
        m = re.search(r"/styles/([^/]+)/", r.get("item_url") or "")
        r["style"] = m.group(1) if m else ""
        rows.append(tuple(r.get(k) for k in fields))
    con.executemany("INSERT INTO registry_items (%s) VALUES (%s)"
                    % (", ".join(fields), ", ".join("?" * len(fields))), rows)
    con.execute("DROP TABLE registry_items_old")
    con.commit()
    return True


def connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    _migrate(con)
    _migrate_registry_items(con)
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


def upsert(con: sqlite3.Connection, rec: dict, not_before: str | None = None) -> str:
    """Insert or update a row. Returns `written` or `skipped-newer`.

    `not_before` is the ISO stamp of the moment the *measuring run* started. A row whose `updated_at`
    is newer than that was written by a run that started later — overwriting it with this run's older
    measurement would silently roll the registry back. Observed for real: two intake runs on the same
    registry, the slower one finishing last and winning.
    """
    rec = {k: rec.get(k) for k in TPL_FIELDS if k in rec} | {
        k: rec[k] for k in ("name", "url") if k in rec
    }
    # normalise json-ish fields
    for f in ("stack", "deps_vendor", "deps_selfhost", "deps_unclassified", "swap_map",
              "rebrand_surface", "risk_flags", "evidence", "details", "features", "locales"):
        if isinstance(rec.get(f), (dict, list)):
            rec[f] = json.dumps(rec[f], ensure_ascii=False)
    stack = jload(rec.get("stack"), {})
    if stack and "canonical" not in rec:
        rec["canonical"], rec["canonical_notes"] = compute_canonical(stack)
    rec["updated_at"] = now()
    cols = [c for c in TPL_FIELDS if c in rec]
    existing = con.execute("SELECT id, risk_flags, updated_at FROM templates WHERE name = ?",
                           (rec.get("name"),)).fetchone()
    if existing and not_before and (existing["updated_at"] or "") > not_before:
        return "skipped-newer"
    if existing and "risk_flags" in rec:
        # intake owns the repo facts, import-details owns the flags it derived from pitfalls:
        # a re-measurement must not silently erase a security blocker.
        kept = [f for f in (jload(existing["risk_flags"], []) or [])
                if isinstance(f, dict) and f.get("source") == "pool-details"]
        if kept:
            incoming = jload(rec.get("risk_flags"), []) or []
            kinds = {f.get("kind") for f in incoming if isinstance(f, dict)}
            rec["risk_flags"] = json.dumps(incoming + [f for f in kept if f.get("kind") not in kinds],
                                           ensure_ascii=False)
    if existing:
        sets = ", ".join(f"{c} = ?" for c in cols)
        con.execute(f"UPDATE templates SET {sets} WHERE name = ?", [rec[c] for c in cols] + [rec["name"]])
    else:
        con.execute(f"INSERT INTO templates ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                    [rec[c] for c in cols])
    con.commit()
    return "written"


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
              "rebrand_surface", "risk_flags", "evidence", "details", "features", "locales"):
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

    # The detail file can prove something the remote heuristic cannot: there is no persistence at all
    # (measured `db: none`). Recommending that for an app that must store data would be a lie with a
    # high score attached, so it is priced in.
    det = row.get("details") if isinstance(row.get("details"), dict) else {}
    det_db = str(((det.get("stack") or {}).get("db")) or "").lower()
    wants = {str(f).lower() for f in (intake.get("features") or [])}
    needs_storage = want_shape in ("saas", "marketplace", "booking", "catalogue") or bool(
        wants & {"accounts", "payments", "files", "admin", "booking"})
    if det_db in ("none", "unknown") and needs_storage:
        s -= 25
        reasons.append(f"penalty: measured stack has NO database (details: db={det_db}) — "
                       f"persistence would be built from scratch")

    for f in (row.get("risk_flags") or []):
        if isinstance(f, dict):
            if f.get("kind") == "stale":
                s -= 20
                reasons.append("penalty: stale upstream")
            elif f.get("kind") == "no-tests":
                s -= 5
                reasons.append("penalty: no tests detected")
            elif f.get("kind") in ("injected-payload", "install-impossible"):
                # Measured from the detail file: never merely a penalty.
                blockers.append(f"{f['kind']}: {f.get('detail', '')[:160]}")
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


# ---------------------------------------------------------------- pool details
# A detail file is written by an agent that read real files: the one thing that must never travel
# back is a credential VALUE. Names are welcome; values are refused (see 10-match.md).
SECRET_RE = re.compile(
    r"sk_live_[A-Za-z0-9]{10,}|sk_test_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{24,}"
    r"|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY|xox[baprs]-[A-Za-z0-9-]{10,}"
)


def _secret_hits(text: str) -> list[str]:
    return sorted({m.group(0)[:10] for m in SECRET_RE.finditer(text)})


def validate_details(rec: dict, text: str) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one pool-detail file. An error keeps it out of the registry."""
    errs: list[str] = []
    warns: list[str] = []
    for k in ("repo", "slug"):
        if not rec.get(k):
            errs.append(f"missing `{k}`")
    hits = _secret_hits(text)
    if hits:
        errs.append(f"credential-shaped value present ({', '.join(hits)}) — values are never recorded")
    for k in ("framework", "stack", "features", "env", "deploy", "tests", "health", "verdict", "evidence"):
        if k not in rec:
            warns.append(f"section `{k}` absent")
    if not rec.get("evidence"):
        warns.append("no `evidence` map — its facts are not traceable")
    if not rec.get("unmeasured"):
        warns.append("no `unmeasured` list")
    for b in (rec.get("blocking") or []):
        if not isinstance(b, dict):
            warns.append("`blocking` entries must be objects")
        elif b.get("kind") not in BLOCKING_KINDS:
            warns.append(f"unknown blocking kind `{b.get('kind')}` "
                         f"(allowed: {', '.join(sorted(BLOCKING_KINDS))})")
        elif not b.get("evidence"):
            warns.append(f"blocking `{b.get('kind')}` carries no evidence")
    return errs, warns


BLOCKING_KINDS = {
    "injected-payload": "security: the shipped code carries an obfuscated/injected blob — never clone",
    "install-impossible": "the repo cannot install as shipped (phantom dependency or missing lockfile)",
}


def _derive_flags(rec: dict, existing: list) -> list[dict]:
    """Blockers from the detail file's own `blocking[]` — a structured claim that carries evidence.

    Deliberately NOT derived from pitfall prose: a regex over an agent's free text gave two healthy
    templates a blocker ("no bun lockfile" while an npm lockfile exists; a passing mention of
    `npm ci`). Structured or nothing — a flagged template is never cloned, so a false flag costs a
    good candidate and a missed one ships a poisoned project.
    """
    keep = [f for f in existing if not (isinstance(f, dict) and f.get("source") == "pool-details")]
    out: list[dict] = []
    for b in (rec.get("blocking") or []):
        if not isinstance(b, dict):
            continue
        kind = b.get("kind")
        if kind not in BLOCKING_KINDS or any(f["kind"] == kind for f in out):
            continue
        out.append({"kind": kind,
                    "detail": f"{BLOCKING_KINDS[kind]} — \"{(b.get('why') or '')[:200]}\"",
                    "evidence": b.get("evidence"), "source": "pool-details"})
    return keep + out


def _promote(rec: dict) -> dict:
    """Queryable columns, so matching never has to parse the blob."""
    i18n = ((rec.get("stack") or {}).get("i18n") or {}) if isinstance(rec.get("stack"), dict) else {}
    raw = str((rec.get("verdict") or {}).get("swap_burden") or "")
    m = re.search(r"\b(none|light|medium|heavy)\b", raw, re.I)   # tolerate prose around the word
    return {
        "features": json.dumps(rec.get("features") or [], ensure_ascii=False),
        "locales": json.dumps(i18n.get("locales") or [], ensure_ascii=False),
        "swap_burden": (m.group(1).lower() if m else (raw.strip() or None)),
    }


def cmd_import_details(con, path: Path, store_dir: Path, as_json: bool) -> int:
    files = [path] if path.is_file() else sorted(p for p in path.glob("*.json"))
    if not files:
        print(f"import-details: no *.json under {path}", file=sys.stderr)
        return 1
    ok: list[tuple[str, str, dict]] = []
    bad: list[tuple[str, list[str]]] = []
    warns: list[str] = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        try:
            rec = json.loads(text)
        except Exception as e:
            bad.append((f.name, [f"invalid JSON: {e}"]))
            continue
        errs, ws = validate_details(rec, text)
        if errs:
            bad.append((f.name, errs))
            continue
        row = con.execute("SELECT name, repo, risk_flags FROM templates WHERE lower(repo) = lower(?)",
                          (rec["repo"],)).fetchone()
        if not row:
            # A repo rename must not break the link — but details for repo X may never be attached to a
            # row that measures repo Y: that would silently lie about the template.
            row = con.execute("SELECT name, repo, risk_flags FROM templates WHERE lower(name) = lower(?)",
                              (rec["slug"],)).fetchone()
            if row and (row["repo"] or "").strip() and (row["repo"] or "").strip().lower() != rec["repo"].lower():
                bad.append((f.name, [f"slug {rec['slug']} matches row '{row['name']}' but that row measures "
                                     f"{row['repo']} — refusing to attach details for {rec['repo']}"]))
                continue
        if not row:
            bad.append((f.name, [f"{rec['repo']} is not in the registry — run "
                                 f"`template_intake.py --repo {rec['repo']}` first"]))
            continue
        store_dir.mkdir(parents=True, exist_ok=True)
        target = store_dir / f"{rec['slug']}.json"
        target.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            shown = str(target.relative_to(SKILL_DIR)).replace("\\", "/")
        except ValueError:
            shown = str(target)
        upd = {"details": json.dumps(rec, ensure_ascii=False), "details_at": now(), "details_file": shown}
        upd.update(_promote(rec))
        flags = _derive_flags(rec, jload(row["risk_flags"], []) or [])
        upd["risk_flags"] = json.dumps(flags, ensure_ascii=False)
        con.execute(f"UPDATE templates SET {', '.join(f'{c} = ?' for c in upd)} WHERE name = ?",
                    [upd[c] for c in upd] + [row["name"]])
        con.commit()
        ok.append((f.name, row["name"], rec))
        warns += [f"{rec['slug']}: {w}" for w in ws]

    if as_json:
        print(json.dumps({"imported": [{"file": a, "template": b} for a, b, _ in ok],
                          "rejected": [{"file": a, "errors": e} for a, e in bad],
                          "warnings": warns}, ensure_ascii=False, indent=2))
    else:
        for fname, tpl, rec in ok:
            pr = _promote(rec)
            feats = len(json.loads(pr["features"]))
            locs = len(json.loads(pr["locales"]))
            print(f"  ok  {fname:38} -> {tpl:28} features={feats:3} locales={locs} "
                  f"swap={pr['swap_burden'] or '?'}")
        for fname, errs in bad:
            print(f"  REFUSED {fname}: {'; '.join(errs)}", file=sys.stderr)
        for w in warns:
            print(f"  warn: {w}")
        print(f"import-details: {len(ok)} imported, {len(bad)} refused, {len(warns)} warning(s)")
    return 0 if ok and not bad else 1


def _digest(r: dict) -> dict:
    """What the bulk export carries: enough to rank and to decide, small enough to read."""
    d = r.get("details") or {}
    if not isinstance(d, dict):
        d = {}
    return {
        "details_file": r.get("details_file"), "details_at": r.get("details_at"),
        "features": r.get("features") or d.get("features") or [],
        "locales": r.get("locales") or ((d.get("stack") or {}).get("i18n") or {}).get("locales") or [],
        "swap_burden": r.get("swap_burden"),
        "verdict": d.get("verdict") or {}, "routes_count": (d.get("routes") or {}).get("count"),
        "tests": d.get("tests") or {},
        "deploy": {k: (d.get("deploy") or {}).get(k) for k in
                   ("docker", "standalone_output", "paas_coupling", "build_cmd", "start_cmd")},
        "pitfalls": [p.get("kind") for p in (d.get("pitfalls") or []) if isinstance(p, dict)],
        "health": d.get("health") or {}, "complexity": d.get("complexity") or {},
    }


def cmd_export(con, out: Path) -> int:
    rows = [rowdict(r) for r in con.execute("SELECT * FROM templates ORDER BY COALESCE(rank, 999), name").fetchall()]
    detailed = 0
    for r in rows:
        r["details_digest"] = _digest(r)
        if r.get("details_file"):
            detailed += 1
        r.pop("details", None)  # the blob lives in SQLite and in data/details/<slug>.json
    payload = {"generated_at": now(), "source": "data/templates.db", "count": len(rows),
               "with_details": detailed, "templates": rows}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"exported {len(rows)} template(s) ({detailed} with deep details) -> {out}")
    return 0


# ------------------------------------------------- component registry (try-on)
REG_FIELDS = ("registry", "item", "style", "type", "title", "description", "categories", "slot", "slot_kind",
              "base", "deps", "registry_deps", "item_url", "index_url", "free", "license",
              "license_evidence", "content_sha", "fetched_at", "updated_at")


def reg_upsert(con: sqlite3.Connection, rec: dict, not_before: str | None = None) -> str:
    """Insert/update one registry item, keyed (registry, item, style). Same stale-run guard as `upsert`."""
    rec = {k: rec.get(k) for k in REG_FIELDS if k in rec}
    rec.setdefault("style", "")
    for f in ("deps", "registry_deps", "categories"):
        if isinstance(rec.get(f), (list, dict)):
            rec[f] = json.dumps(rec[f], ensure_ascii=False)
    rec["updated_at"] = now()
    cur = con.execute("SELECT updated_at FROM registry_items WHERE registry = ? AND item = ? AND style = ?",
                      (rec.get("registry"), rec.get("item"), rec.get("style"))).fetchone()
    if cur and not_before and (cur["updated_at"] or "") > not_before:
        return "skipped-newer"
    cols = [c for c in REG_FIELDS if c in rec]
    if cur:
        con.execute(f"UPDATE registry_items SET {', '.join(c + ' = ?' for c in cols)} "
                    "WHERE registry = ? AND item = ? AND style = ?",
                    [rec[c] for c in cols] + [rec["registry"], rec["item"], rec.get("style", "")])
    else:
        con.execute(f"INSERT INTO registry_items ({', '.join(cols)}) "
                    f"VALUES ({', '.join('?' * len(cols))})", [rec[c] for c in cols])
    con.commit()
    return "written"


def reg_rows(con: sqlite3.Connection, slot: str | None = None, base: str | None = None,
             free_only: bool = False, registry: str | None = None) -> list[sqlite3.Row]:
    q = "SELECT * FROM registry_items WHERE 1=1"
    args: list = []
    if slot:
        q += " AND slot = ?"
        args.append(slot)
    if base:
        q += " AND (base IS NULL OR base = 'none' OR base = ?)"
        args.append(base)
    if free_only:
        q += " AND free = 1"
    if registry:
        q += " AND registry = ?"
        args.append(registry)
    return list(con.execute(q + " ORDER BY registry, item", args))


def reg_run_start(con: sqlite3.Connection, started_at: str, style: str) -> int:
    cur = con.execute("INSERT INTO registry_runs (started_at, style) VALUES (?, ?)", (started_at, style))
    con.commit()
    return int(cur.lastrowid)


def reg_run_finish(con: sqlite3.Connection, run_id: int, registries: str, written: int, skipped: int) -> None:
    con.execute("UPDATE registry_runs SET finished_at = ?, registries = ?, written = ?, skipped = ? WHERE id = ?",
                (now(), registries, written, skipped, run_id))
    con.commit()


def reg_run_is_stale(con: sqlite3.Connection, run_start: str) -> bool:
    """True when a run that STARTED later already COMPLETED. A stalled or replayed run must never
    write old-policy rows over a newer generation — per-row guards cannot see rows it alone touches."""
    row = con.execute("SELECT COUNT(*) c FROM registry_runs WHERE finished_at IS NOT NULL AND started_at > ?",
                      (run_start,)).fetchone()
    return bool(row["c"])


def reg_slots(con: sqlite3.Connection, free_only: bool = False) -> list[dict]:
    q = ("SELECT slot, slot_kind, COUNT(*) n, SUM(CASE WHEN free = 1 THEN 1 ELSE 0 END) n_free "
         "FROM registry_items WHERE slot IS NOT NULL GROUP BY slot, slot_kind "
         "ORDER BY slot_kind DESC, slot")  # primitives first: v1 swaps single components (blocks are v1.5)
    return [dict(r) for r in con.execute(q)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Template Factory registry (SQLite truth + JSON export)")
    ap.add_argument("--db", default=str(DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init"); p.add_argument("--seed", default=str(SKILL_DIR / "data" / "templates.seed.json")); p.add_argument("--force", action="store_true")
    p = sub.add_parser("import"); p.add_argument("path")
    p = sub.add_parser("list"); p.add_argument("--status", choices=STATUSES); p.add_argument("--shape", choices=SHAPES); p.add_argument("--canonical", action="store_true"); p.add_argument("--json", action="store_true")
    p = sub.add_parser("score"); p.add_argument("--intake", required=True); p.add_argument("--top", type=int, default=3); p.add_argument("--json", action="store_true")
    p = sub.add_parser("export"); p.add_argument("--out", default=str(DEFAULT_EXPORT))
    p = sub.add_parser("import-details"); p.add_argument("path"); p.add_argument("--store", default=str(SKILL_DIR / "data" / "details")); p.add_argument("--json", action="store_true")
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
    if args.cmd == "import-details":
        return cmd_import_details(con, Path(args.path), Path(args.store), args.json)
    return 1


if __name__ == "__main__":
    sys.exit(main())
