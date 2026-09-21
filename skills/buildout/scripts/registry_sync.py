#!/usr/bin/env python3
"""registry_sync.py - living shadcn-registry pool for the buildout skill.

sync    fetch https://ui.shadcn.com/r/registries.json -> filter by health ->
        merge MIT allowlist -> write compact data/registries.snapshot.json
check   print snapshot age / staleness (no network)
list    query the snapshot cheaply (--match substring, --limit)
onboard fetch <registry>/r/registry.json (or --catalog-file <path>) ->
        data/items/<ns>.jsonl candidates

Stdlib only, Python 3.10+. Never print the full directory JSON.
"""
import argparse, json, sys, time, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SNAPSHOT = DATA / "registries.snapshot.json"
ALLOWLIST = DATA / "allowlist.json"
ITEMS_DIR = DATA / "items"
SOURCE = "https://ui.shadcn.com/r/registries.json"
UA = {"User-Agent": "deckhand-buildout/0.2 (+agentskills.io)"}
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
KEEP_STATUSES = {"healthy"}

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def fetch_json(url):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        if err.code in (403, 429):
            req2 = urllib.request.Request(url, headers=BROWSER_UA)
            with urllib.request.urlopen(req2, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        raise

def compact_entry(e, min_score):
    h = e.get("health") or {}
    if h.get("hidden") is True:
        return None
    if h.get("status") not in KEEP_STATUSES:
        return None
    score = h.get("score")
    if score is None or float(score) < min_score:
        return None
    return {
        "name": e.get("name"),
        "url": e.get("url"),
        "homepage": e.get("homepage"),
        "description": (e.get("description") or "")[:160],
        "score": round(float(score), 1),
        "checkedAt": h.get("checkedAt"),
        "firstObservedAt": h.get("firstObservedAt"),
        "inAllowlist": False, "license": None, "tags": [], "integration": "shadcn",
    }

def merge_allowlist(entries, allow):
    by_name = {e["name"]: e for e in entries}
    for a in allow.get("registries", []):
        name = a["name"]
        if name in by_name:
            t = by_name[name]
            t["inAllowlist"] = True
            t["license"] = a.get("license")
            t["licenseEvidence"] = a.get("licenseEvidence")
            t["integration"] = a.get("integration", "shadcn")
            t["tags"] = sorted(set(t.get("tags", [])) | set(a.get("tags", [])))
            t["notes"] = a.get("notes", "")
        else:
            entries.append({
                "name": name, "url": a.get("url"), "homepage": a.get("homepage"),
                "description": (a.get("notes") or "")[:160], "score": None,
                "checkedAt": None, "firstObservedAt": None, "inAllowlist": True,
                "license": a.get("license"), "licenseEvidence": a.get("licenseEvidence"),
                "integration": a.get("integration", "shadcn"),
                "tags": sorted(set(a.get("tags", []))), "notes": a.get("notes", ""),
            })
    return entries

def cmd_sync(args):
    allow = json.loads(ALLOWLIST.read_text(encoding="utf-8"))
    if SNAPSHOT.exists() and not args.force and not args.fixture:
        try:
            age_days = (time.time() - float(json.loads(SNAPSHOT.read_text(encoding="utf-8")).get("fetchedAtEpoch", 0))) / 86400
            if age_days < args.ttl_days:
                print(f"snapshot fresh ({age_days:.1f}d < {args.ttl_days}d) - use --force to refresh")
                return 0
        except Exception:
            pass
    if args.fixture:
        directory = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        src = f"fixture:{args.fixture}"
    else:
        try:
            directory = fetch_json(SOURCE)
        except Exception as err:
            print(f"could not fetch {SOURCE}: {err}")
            return 1
        src = SOURCE
    kept = [c for c in (compact_entry(e, args.min_score) for e in directory) if c]
    kept = merge_allowlist(kept, allow)
    kept.sort(key=lambda e: e["name"].lower())
    prev = set()
    if SNAPSHOT.exists():
        try:
            prev = {e["name"] for e in json.loads(SNAPSHOT.read_text(encoding="utf-8")).get("registries", [])}
        except Exception:
            pass
    new = sorted({e["name"] for e in kept} - prev)
    DATA.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({
        "fetchedAt": now_iso(), "fetchedAtEpoch": time.time(), "source": src,
        "minScore": args.min_score, "counts": {"directory": len(directory), "kept": len(kept)},
        "registries": kept,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"synced: {len(directory)} listed -> {len(kept)} kept (status healthy, score >= {args.min_score}, + allowlist)")
    if new:
        head = ", ".join(new[:10]) + (f" (+{len(new) - 10} more)" if len(new) > 10 else "")
        print(f"new since last snapshot: {head}")
    else:
        print("new since last snapshot: -")
    print(f"wrote {SNAPSHOT}")
    return 0

def cmd_check(args):
    if not SNAPSHOT.exists():
        print("no snapshot - run: py scripts/registry_sync.py sync")
        return 1
    d = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    age_days = (time.time() - float(d.get("fetchedAtEpoch", 0))) / 86400
    print(f"snapshot: {d['counts']['kept']} kept of {d['counts']['directory']} | fetched {d.get('fetchedAt')} | age {age_days:.1f}d | stale={age_days > args.ttl_days}")
    return 0

def cmd_list(args):
    if not SNAPSHOT.exists():
        print("no snapshot - run: py scripts/registry_sync.py sync")
        return 1
    d = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    pat = args.match.lower()
    rows = [e for e in d["registries"] if not pat or pat in json.dumps(e, ensure_ascii=False).lower()]
    for e in rows[:args.limit]:
        mark = "*" if e.get("inAllowlist") else " "
        print(f"{mark}{e['name']:<22} score={str(e.get('score')):<6} {e.get('integration', 'shadcn'):<14} {e.get('homepage', '')}  {e.get('notes') or (e.get('description') or '')[:60]}")
    print(f"({len(rows)} match, showing {min(len(rows), args.limit)})")
    return 0

def cmd_onboard(args):
    if not SNAPSHOT.exists():
        print("no snapshot - run: py scripts/registry_sync.py sync")
        return 1
    d = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    entry = next((e for e in d["registries"] if e["name"] == args.namespace), None)
    if entry is None:
        print(f"registry {args.namespace} not in snapshot - add to allowlist + sync first")
        return 1
    base = (entry.get("homepage") or "").rstrip("/")
    catalog_url = base + "/r/registry.json"
    if args.catalog_file:
        try:
            cat = json.loads(Path(args.catalog_file).read_text(encoding="utf-8"))
        except Exception as err:
            print(f"could not read catalog file {args.catalog_file}: {err}")
            return 1
        source_note = f"file:{args.catalog_file}"
    else:
        try:
            cat = fetch_json(catalog_url)
        except Exception as err:
            print(f"could not fetch catalog {catalog_url}: {err}")
            return 1
        source_note = catalog_url
    items = cat.get("items", []) if isinstance(cat, dict) else []
    tmpl = entry.get("url") or ""
    ns_file = entry["name"].lstrip("@").lower().replace("/", "-")
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    out = ITEMS_DIR / f"{ns_file}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for it in items:
            name = it.get("name")
            if not name:
                continue
            if "{style}" in tmpl:
                install = "npx shadcn@latest add " + tmpl.replace("{style}", args.style).replace("{name}", name)
            else:
                install = "npx shadcn@latest add " + (tmpl.replace("{name}", name) if tmpl else name)
            fh.write(json.dumps({
                "id": f"{entry['name']}/{name}", "name": name, "registry": entry["name"],
                "type": it.get("type"), "title": it.get("title"),
                "description": (it.get("description") or "")[:160],
                "deps": it.get("dependencies", []), "registryDeps": it.get("registryDependencies", []),
                "install": install, "catalog": catalog_url, "catalogSource": source_note, "addedAt": now_iso(),
            }, ensure_ascii=False) + "\n")
    print(f"onboarded {entry['name']}: {len(items)} items -> {out} (source: {source_note})")
    return 0

def main():
    ap = argparse.ArgumentParser(description="shadcn registry pool sync")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync"); s.add_argument("--force", action="store_true"); s.add_argument("--min-score", type=float, default=85); s.add_argument("--ttl-days", type=float, default=7); s.add_argument("--fixture"); s.set_defaults(fn=cmd_sync)
    c = sub.add_parser("check"); c.add_argument("--ttl-days", type=float, default=7); c.set_defaults(fn=cmd_check)
    l = sub.add_parser("list"); l.add_argument("--match", default=""); l.add_argument("--limit", type=int, default=25); l.set_defaults(fn=cmd_list)
    o = sub.add_parser("onboard"); o.add_argument("namespace"); o.add_argument("--style", default="radix"); o.add_argument("--catalog-file", default=None); o.set_defaults(fn=cmd_onboard)
    args = ap.parse_args()
    return args.fn(args)

if __name__ == "__main__":
    sys.exit(main())
