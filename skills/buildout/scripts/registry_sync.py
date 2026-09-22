#!/usr/bin/env python3
"""registry_sync.py - living shadcn-registry pool for the buildout skill.

sync    fetch https://ui.shadcn.com/r/registries.json -> carry every non-hidden
        entry (unhealthy kept + healthStatus-marked, never dropped) -> merge MIT
        allowlist -> write compact data/registries.snapshot.json
check   print snapshot age / staleness (no network)
list    query the snapshot cheaply (--match substring, --limit)
onboard fetch <registry>/r/registry.json (or --catalog-file <path>) ->
        data/items/<ns>.jsonl candidates ({style} URL templates use --style;
        sampled install URLs are live-verified BEFORE writing - 404 aborts)
verify  live-check every allowlisted registry's install path (index + sampled
        items; --item @ns/<name> checks one item) - verdict 'ok' requires EVERY
        sample 200; a free/gated mix reads 'mixed' and FAILS; fails on 404
        templates, all-gated/mixed registries and unsynced allowlists

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
DEFAULT_STYLE = "base-nova"  # value baked into {style} URL templates; reui reads <base>-<variant>
                             # and serves only its listed pairs (default base-nova, verified 2026-09-21)
SAMPLE_COUNT = 5             # spread sampled per registry by onboard/verify
VERIFY_FAIL = {"dead", "gated", "mixed", "error", "unverified"}  # 'mixed' = some samples free, some not -> cannot vouch for the registry
VERIFY_SAMPLE_COUNT = 12     # whole-pool verify default: 5 evenly-spread samples cannot characterise a 474-item registry
BARE_OK_NS = "@shadcn"       # the CLI's own default registry - bare-name installs are correct only here

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

def fetch_status(url):
    """HTTP status for one GET (browser UA); 'ERR:<kind>' on transport failure."""
    req = urllib.request.Request(url, headers=BROWSER_UA)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:
        return "ERR:" + type(e).__name__

def compact_entry(e, min_score):
    """Carry EVERY non-hidden directory entry - unhealthy / low-score rows are
    kept and healthStatus-marked (the `list` view filters them by default, but
    'not in the list' must never mean 'does not exist'; min_score is applied at
    list time, not here)."""
    h = e.get("health") or {}
    if h.get("hidden") is True:
        return None
    score = h.get("score")
    return {
        "name": e.get("name"),
        "url": e.get("url"),
        "homepage": e.get("homepage"),
        "description": (e.get("description") or "")[:160],
        "score": round(float(score), 1) if score is not None else None,
        "healthStatus": h.get("status"),
        "checkedAt": h.get("checkedAt"),
        "firstObservedAt": h.get("firstObservedAt"),
        "inAllowlist": False, "license": None, "tags": [], "integration": "shadcn",
    }

def in_default_view(e, min_score):
    """Show in `list` without --all: healthy + score >= min_score, or allowlisted."""
    if e.get("inAllowlist"):
        return True
    if e.get("healthStatus") not in KEEP_STATUSES:
        return False
    sc = e.get("score")
    return sc is not None and float(sc) >= min_score

def merge_allowlist(entries, allow):
    by_name = {e["name"]: e for e in entries}
    for a in allow.get("registries", []):
        name = a["name"]
        if name in by_name:
            t = by_name[name]
            t["inAllowlist"] = True
            if "url" in a:
                # Curated fields win over the directory's; an explicit null url = bare-name installs.
                t["url"] = a.get("url")
            if a.get("homepage"):
                t["homepage"] = a["homepage"]
            if a.get("catalogUrl"):
                t["catalogUrl"] = a["catalogUrl"]
            if a.get("verifiedAt"):
                t["verifiedAt"] = a["verifiedAt"]
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
                **({"catalogUrl": a["catalogUrl"]} if a.get("catalogUrl") else {}),
                **({"verifiedAt": a["verifiedAt"]} if a.get("verifiedAt") else {}),
            })
    return entries

def render_install(tmpl, name, style):
    """Final `npx shadcn add` target for one catalog item (bare name when no template)."""
    tmpl = tmpl or ""
    if "{style}" in tmpl:
        target = tmpl.replace("{style}", style).replace("{name}", name)
    else:
        target = tmpl.replace("{name}", name) if tmpl else name
    return "npx shadcn@latest add " + target

def install_target(install):
    """The URL inside an install string; None for bare-name installs (CLI-resolved)."""
    prefix = "npx shadcn@latest add "
    t = install[len(prefix):] if (install or "").startswith(prefix) else (install or "")
    return t if t.startswith("http") else None

def catalog_items(cat):
    """Items from a registry index: {'items': [...]} or a bare JSON list."""
    if isinstance(cat, dict):
        return cat.get("items", []) or []
    return cat if isinstance(cat, list) else []

def sample_indices(n, count=SAMPLE_COUNT):
    """Evenly spread sample indices over n items (first ... last always included)."""
    if n <= 0:
        return []
    if n <= count:
        return list(range(n))
    return sorted({round(i * (n - 1) / (count - 1)) for i in range(count)})

def classify_samples(statuses):
    """Verdict from sampled install statuses: int = HTTP, None = bare name, str = transport error.
    'ok' requires EVERY int sample == 200 - one free item must not vouch for a
    mostly-gated registry (that reading shipped a 401-storm as 'ok' once). A
    free/gated mix is 'mixed' and FAILS the whole-pool gate."""
    ints = [s for s in statuses if isinstance(s, int)]
    if ints:
        if any(isinstance(s, str) for s in statuses):
            return "error"
        if all(s == 200 for s in ints):
            return "ok"
        if any(s == 404 for s in ints):
            return "dead"
        if all(s in (401, 402, 403) for s in ints):
            return "gated"
        if all(s == 429 for s in ints):
            return "rate-limited"
        if any(s == 200 for s in ints):
            return "mixed"
        return "error"
    if statuses and all(s is None for s in statuses):
        return "bare"
    if any(isinstance(s, str) for s in statuses):
        return "error"
    return "unverified"

def free_ratio(statuses):
    """(free, total) over int samples - printed so a ratio is never hidden."""
    ints = [s for s in statuses if isinstance(s, int)]
    return (sum(1 for s in ints if s == 200), len(ints))

def display_status(st):
    return "bare" if st is None else str(st)

def catalog_url_for(entry):
    return entry.get("catalogUrl") or ((entry.get("homepage") or "").rstrip("/") + "/r/registry.json")

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
    healthy = sum(1 for e in kept if in_default_view(e, args.min_score))
    DATA.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(json.dumps({
        "fetchedAt": now_iso(), "fetchedAtEpoch": time.time(), "source": src,
        "minScore": args.min_score, "counts": {"directory": len(directory), "kept": len(kept), "healthy": healthy},
        "registries": kept,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"synced: {len(directory)} listed -> {len(kept)} carried ({healthy} in the default list view; unhealthy/low kept and marked, hidden=true dropped; allowlist merged)")
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
    min_score = float(d.get("minScore", 85))
    pat = args.match.lower()
    rows = [e for e in d["registries"] if not pat or pat in json.dumps(e, ensure_ascii=False).lower()]
    in_view = [e for e in rows if in_default_view(e, min_score)]
    hidden = len(rows) - len(in_view)
    scope = rows if (args.all or pat) else in_view   # an explicit --match shows filtered matches too (marked ~)
    print("* = MIT-allowlisted; *+ = allowlisted AND onboarded (installable today); ~ = normally filtered by health/score (kept in the snapshot - --all shows them); unmarked = directory entry, license unverified - do not install or onboard from it")
    for e in scope[:args.limit]:
        ns_file = e["name"].lstrip("@").lower().replace("/", "-")
        onboarded = (ITEMS_DIR / f"{ns_file}.jsonl").exists()
        mark = ("~" if not in_default_view(e, min_score) else " ") + ("*" if e.get("inAllowlist") else " ") + ("+" if onboarded else " ")
        print(f"{mark} {e['name']:<22} st={str(e.get('healthStatus') or '-'):<9} score={str(e.get('score')):<6} {e.get('integration', 'shadcn'):<14} {e.get('homepage', '')}  {e.get('notes') or (e.get('description') or '')[:60]}")
    footer = f"; {hidden} registr{'y' if hidden == 1 else 'ies'} hidden by the health/score filter (list --all shows them)" if (hidden and not args.all and not pat) else ""
    print(f"({len(rows)} match, showing {min(len(scope), args.limit)})" + footer)
    return 0

def cmd_onboard(args):
    if not SNAPSHOT.exists():
        print("no snapshot - run: py scripts/registry_sync.py sync")
        return 1
    d = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    entry = next((e for e in d["registries"] if e["name"] == args.namespace), None)
    if entry is None or not entry.get("inAllowlist"):
        why = "not in the snapshot" if entry is None else "not MIT-allowlisted"
        print(f"registry {args.namespace} is {why} - add this entry to data/allowlist.json, then run `sync`. Entry shape (all fields required):")
        print('  {"name": "' + args.namespace + '", "homepage": "https://<host>", "url": "https://<host>/r/{name}.json",')
        print('   "license": "MIT", "licenseEvidence": "<repo LICENSE URL, or `gh api repos/<o>/<r> --jq .license.spdx_id` output> dated",')
        print('   "verifiedAt": "YYYY-MM-DD", "tags": ["marketing"], "notes": "<working URL shape + any gated subset, from live statuses>"}')
        print('  Index served elsewhere? add "catalogUrl": "https://<host>/<index-path>". Index throttled? retry with onboard --catalog-file <saved index>.')
        return 1
    catalog_url = catalog_url_for(entry)
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
            print('  If this is 404/410/throttled: set "catalogUrl" in data/allowlist.json to the served index path, re-run `sync`, then retry - or pass --catalog-file <saved index file> (repo mirror).')
            return 1
        source_note = catalog_url
    rows = []
    for it in catalog_items(cat):
        if not isinstance(it, dict) or not it.get("name"):
            continue
        name = it["name"]
        rows.append({
            "id": f"{entry['name']}/{name}", "name": name, "registry": entry["name"],
            "type": it.get("type"), "title": it.get("title"),
            "description": (it.get("description") or "")[:160],
            "deps": it.get("dependencies", []), "registryDeps": it.get("registryDependencies", []),
            "install": render_install(entry.get("url"), name, args.style),
            "catalog": catalog_url, "catalogSource": source_note, "addedAt": now_iso(),
        })
    if not args.no_verify and rows:
        picks = [rows[i] for i in sample_indices(len(rows))]
        print(f"verify: sampling {len(picks)}/{len(rows)} rendered install URLs (--no-verify to skip)")
        statuses = []
        for r in picks:
            target = install_target(r["install"])
            st = fetch_status(target) if target else None
            statuses.append(st)
            print(f"  {display_status(st):>12}  {r['id']}" + (f"  {target}" if target else ""))
        verdict = classify_samples(statuses)
        if verdict == "dead":
            print("onboard ABORTED: sampled install URLs return 404 - the allowlist url template or --style is not served.")
            print("Fix data/allowlist.json (url / --style) first; nothing was written.")
            return 1
        if verdict not in ("ok", "bare"):
            free, tot = free_ratio(statuses)
            print(f"onboard warning: sampled verdict '{verdict}' ({free}/{tot} free) - some or all sampled install URLs are gated; 'ok' now requires EVERY sample free, so `verify` will fail this registry until the gated subset is excluded or documented.")
        elif not entry.get("url") and entry["name"] != BARE_OK_NS:
            print("onboard warning: url is null - bare-name installs are only correct for the CLI's own default registry; give this entry a url template in data/allowlist.json.")
        else:
            print(f"onboard verify: {verdict}")
    ns_file = entry["name"].lstrip("@").lower().replace("/", "-")
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    out = ITEMS_DIR / f"{ns_file}.jsonl"
    with out.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"onboarded {entry['name']}: {len(rows)} items -> {out} (source: {source_note})")
    return 0

def cmd_verify(args):
    """Live-check the install path of every allowlisted registry (or the named ones)."""
    if not SNAPSHOT.exists():
        print("no snapshot - run: py scripts/registry_sync.py sync")
        return 1
    d = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    allow_names = [a["name"] for a in json.loads(ALLOWLIST.read_text(encoding="utf-8")).get("registries", [])]
    snap_names = {e["name"] for e in d["registries"]}
    missing = [n for n in allow_names if n not in snap_names]
    if missing:
        print(f"verify: {', '.join(missing)} in the allowlist but not in the snapshot - run sync first (verify reads the snapshot)")
        return 1
    entries = [e for e in d["registries"] if e.get("inAllowlist")]
    if args.namespaces:
        entries = [e for e in entries if e["name"] in args.namespaces]
    if args.item:
        ns, _, name = args.item.partition("/")
        entry = next((e for e in entries if e["name"] == ns), None)
        if entry is None or not name:
            print(f"verify: {args.item} is not an allowlisted item (use @ns/<name>)")
            return 1
        ns_file = ns.lstrip("@").lower().replace("/", "-")
        cat_path = ITEMS_DIR / f"{ns_file}.jsonl"
        install = None
        if cat_path.exists():
            for line in cat_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    r = json.loads(line)
                    if r.get("id") == args.item:
                        install = r.get("install")
                        break
        if not install:
            install = render_install(entry.get("url"), name, DEFAULT_STYLE)
        target = install_target(install)
        st = fetch_status(target) if target else None
        verdict = classify_samples([st])
        ok = verdict == "ok" or (verdict == "bare" and ns == BARE_OK_NS)
        print(f"{args.item}: {display_status(st)} ({verdict})" + ("" if ok else " - gated or dead; do not install"))
        return 0 if ok else 1
    failing = 0
    for entry in entries:
        ns = entry["name"]
        if entry.get("integration", "shadcn") != "shadcn":
            print(f" {ns:<21} skip          (integration={entry.get('integration')} - not a shadcn registry)")
            continue
        ns_file = ns.lstrip("@").lower().replace("/", "-")
        cat_path = ITEMS_DIR / f"{ns_file}.jsonl"
        if cat_path.exists():
            rows = [json.loads(l) for l in cat_path.read_text(encoding="utf-8").splitlines() if l.strip()]
            source = f"catalog {ns_file}.jsonl"
        else:
            catalog_url = catalog_url_for(entry)
            try:
                cat = fetch_json(catalog_url)
            except Exception as err:
                print(f"!{ns:<21} index-error   {catalog_url}: {err}")
                failing += 1
                continue
            rows = [{"id": f"{ns}/{it['name']}", "install": render_install(entry.get("url"), it["name"], DEFAULT_STYLE)}
                    for it in catalog_items(cat) if isinstance(it, dict) and it.get("name")]
            source = catalog_url
        if not rows:
            print(f"!{ns:<21} no-items      (empty catalog/index)")
            failing += 1
            continue
        picks = [rows[i] for i in sample_indices(len(rows), args.count)]
        statuses, detail = [], []
        for r in picks:
            target = install_target(r.get("install") or "")
            st = fetch_status(target) if target else None
            statuses.append(st)
            detail.append(f"{r.get('id')}->{display_status(st)}")
        verdict = classify_samples(statuses)
        free, tot = free_ratio(statuses)
        bad = verdict in VERIFY_FAIL or (verdict == "bare" and ns != BARE_OK_NS)
        if bad:
            failing += 1
        print(f"{'!' if bad else ' '}{ns:<21} {verdict:<13} {free}/{tot} free [{source}] " + " | ".join(detail))
    print(f"verify: {len(entries)} checked, {failing} failing (verdict 'ok' requires EVERY sample free; 'mixed' = free/gated mix -> fail)" + ("" if failing == 0 else " - fix the url/note or drop the entry (data/allowlist.json)"))
    return 1 if failing else 0

def main():
    ap = argparse.ArgumentParser(description="shadcn registry pool sync")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync"); s.add_argument("--force", action="store_true"); s.add_argument("--min-score", type=float, default=85); s.add_argument("--ttl-days", type=float, default=7); s.add_argument("--fixture"); s.set_defaults(fn=cmd_sync)
    c = sub.add_parser("check"); c.add_argument("--ttl-days", type=float, default=7); c.set_defaults(fn=cmd_check)
    l = sub.add_parser("list"); l.add_argument("--match", default=""); l.add_argument("--limit", type=int, default=25); l.add_argument("--all", action="store_true", help="include rows normally filtered by health/score"); l.set_defaults(fn=cmd_list)
    o = sub.add_parser("onboard"); o.add_argument("namespace"); o.add_argument("--style", default=DEFAULT_STYLE, help="style baked into {style} URL templates (reui: <base>-<variant>, e.g. base-nova, radix-lyra)"); o.add_argument("--catalog-file", default=None); o.add_argument("--no-verify", action="store_true", help="skip the live sample check of rendered install URLs"); o.set_defaults(fn=cmd_onboard)
    v = sub.add_parser("verify"); v.add_argument("namespaces", nargs="*"); v.add_argument("--count", type=int, default=VERIFY_SAMPLE_COUNT); v.add_argument("--item", default=None, help="check one item, e.g. --item @reui/c-alert-1"); v.set_defaults(fn=cmd_verify)
    args = ap.parse_args()
    return args.fn(args)

if __name__ == "__main__":
    sys.exit(main())
