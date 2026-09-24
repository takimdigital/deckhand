#!/usr/bin/env python3
"""tryon_intake — measure MIT component registries into the SQLite registry (try-on catalog).

Remote-only (no clones, no execution). One index fetch per registry; every item is normalized,
license-gated at the REGISTRY level, classified by base (radix | base-ui | aria | none) with the
measured rule, and slotted by keyword. The raw index is snapshotted with its sha256 first.

    py scripts/tryon_intake.py                      # all usable registries, default style
    py scripts/tryon_intake.py --registry shadcn --style base-nova
    py scripts/tryon_intake.py --json               # machine summary
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

import templates_db as DB

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
ROSTER = SKILL / "data" / "registries.json"
SNAPDIR = SKILL / "data" / "registry-snapshots"
EVIDENCE = SKILL / "data" / "registry-evidence.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

# One keyword list per slot. Matching is word-boundary over a lowercased haystack
# (name + title + description + categories + file paths) — a floor estimate, not a promise.
SLOT_KEYWORDS: dict[str, list[str]] = {
    "button": ["button"], "badge": ["badge", "pill", "chip"], "card": ["card"],
    "input": ["input"], "textarea": ["textarea", "text-area"], "select": ["select", "combobox"],
    "checkbox": ["checkbox"], "radio-group": ["radio"], "switch": ["switch", "toggle"],
    "slider": ["slider", "range"], "dialog": ["dialog", "modal"],
    "dropdown-menu": ["dropdown", "menu"], "tooltip": ["tooltip"], "popover": ["popover"],
    "tabs": ["tabs", "tabbed"], "accordion": ["accordion", "collapsible"],
    "avatar": ["avatar"], "table": ["table"], "sheet": ["sheet", "drawer"],
    "command": ["command", "cmdk"], "toast": ["toast", "sonner"], "breadcrumb": ["breadcrumb"],
    "pagination": ["pagination", "pager"], "progress": ["progress"],
    "skeleton": ["skeleton"],
    "hero": ["hero"], "pricing": ["pricing", "price"], "navbar": ["navbar", "nav", "header"],
    "footer": ["footer"], "cta": ["cta", "call-to-action"], "faq": ["faq"],
    "testimonials": ["testimonial", "review"], "login": ["login", "sign-in", "signin"],
    "signup": ["signup", "sign-up", "register"],
}
BLOCK_SLOTS = {"hero", "pricing", "navbar", "footer", "cta", "faq", "testimonials", "login", "signup"}


def fetch(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def classify_base(deps: list[str], registry_deps: list[str]) -> str:
    """Measured rule (1,489 real items): PANEL precedence base-ui > aria > radix, over deps UNION
    registry deps — a base-ui dep wins even when a radix dep is listed first."""
    all_deps = list(deps) + list(registry_deps)

    def any_match(*pats: str) -> bool:
        return any(re.match(p, d) for p in pats for d in all_deps)

    if any_match(r"^@base-ui/", r"^@base-ui-components/"):
        return "base-ui"
    if any_match(r"^react-aria-components$", r"^@react-aria/", r"^@react-stately/", r"^@react-types/"):
        return "aria"
    if any_match(r"^radix-ui$", r"^@radix-ui/"):
        return "radix"
    return "none"


def classify_slot(hay: str) -> tuple[str | None, str | None]:
    """Earliest keyword match wins (ties -> longer keyword), so `pricing-table-three` is a pricing
    block and `shimmer-button` is a button. A floor estimate, not a promise."""
    low = hay.lower()
    best: tuple[int, int, str] | None = None
    for slot, kws in SLOT_KEYWORDS.items():
        for kw in kws:
            m = re.search(r"(?<![a-z0-9])" + re.escape(kw), low)
            if not m:
                continue
            key = (m.start(), -len(kw), slot)
            if best is None or key < best:
                best = key
    if best is None:
        return None, None
    slot = best[2]
    return slot, ("block" if slot in BLOCK_SLOTS else "primitive")


def item_files(it: dict) -> list[str]:
    return [f.get("path", "") for f in (it.get("files") or []) if isinstance(f, dict)]


def normalize(reg: dict, style: str, items: list[dict], index_url: str,
              probe: dict | None = None) -> list[dict]:
    """probe: {type: bool} from probe_families() — the sampled verdict that a type family's per-item
    endpoint serves embedded content. When probe is None (unit tests, offline) we fall back to the
    index's own embedded content, which is the strictly-safer rule."""
    free_types = set(reg.get("free_types") or [])
    out = []
    for it in items:
        name = it.get("name") or ""
        if not name:
            continue
        deps = list(it.get("dependencies") or []) + list(it.get("devDependencies") or [])
        rdeps = list(it.get("registryDependencies") or [])
        files = item_files(it)
        # a registry item must embed file content to be installable (path-only entries are dropped silently)
        has_content = any(isinstance(f, dict) and f.get("content") for f in (it.get("files") or []))
        content_ok = has_content or bool((probe or {}).get(it.get("type")))
        cats = it.get("categories") or (it.get("meta") or {}).get("categories") or []
        hay = " ".join([name, it.get("title") or "", it.get("description") or "",
                        " ".join(cats if isinstance(cats, list) else [str(cats)]), " ".join(files)])
        slot, kind = classify_slot(hay)
        free = True
        if free_types:
            free = (it.get("type") in free_types)
        # collision guard: items owning lib/utils.ts must never be installed over ours
        if any("utils" in f and "lib" in f for f in files) and name not in ("utils",):
            free = False
        stable = json.dumps({"n": name, "t": it.get("type"), "d": sorted(deps),
                             "r": sorted(rdeps), "f": sorted(files), "x": it.get("title")},
                            sort_keys=True, ensure_ascii=False)
        out.append({
            "registry": reg["id"], "item": name, "type": it.get("type"), "style": style,
            "title": it.get("title") or "", "description": (it.get("description") or "")[:300],
            "categories": cats, "slot": slot, "slot_kind": kind,
            # a style-scoped registry KNOWS its base from the style family (shadcn base-nova ships
            # Base UI code under the same item names as new-york-v4's Radix code) — the style wins
            "base": (reg.get("base_for_style") or {}).get(style) or classify_base(deps, rdeps),
            "deps": deps, "registry_deps": rdeps,
            "item_url": reg["item_url"].replace("{style}", style).replace("{name}", name),
            "index_url": index_url,
            "free": 1 if (free and content_ok) else 0,
            "license": reg["license"], "license_evidence": reg["license_evidence"],
            "content_sha": hashlib.sha256(stable.encode()).hexdigest()[:16],
            "fetched_at": DB.now(),
        })
    return out


def probe_families(reg: dict, style: str, items: list[dict], sample: int = 3) -> dict:
    """Sample up to `sample` items per free TYPE family and fetch each item's own endpoint.
    A family is free only if at least one sampled item serves embedded content (the CLI silently
    drops content-less items, so this is exactly the installability question)."""
    free_types = set(reg.get("free_types") or [])
    families: dict[str, list[dict]] = {}
    for it in items:
        t = it.get("type") or "?"
        if free_types and t not in free_types:
            continue
        fam = families.setdefault(t, [])
        if len(fam) < sample:
            fam.append(it)
    types_ok: dict[str, bool] = {}
    samples: list[dict] = []
    for t, its in sorted(families.items()):
        ok_n = 0
        for it in its:
            url = reg["item_url"].replace("{style}", style).replace("{name}", it.get("name") or "")
            try:
                d = json.loads(fetch(url))
                ok = any(isinstance(f, dict) and f.get("content") for f in (d.get("files") or []))
                samples.append({"url": url, "type": t, "ok": bool(ok)})
            except Exception as e:  # a dead sample is evidence, not a crash
                ok = False
                samples.append({"url": url, "type": t, "ok": False, "error": type(e).__name__})
            ok_n += bool(ok)
        types_ok[t] = ok_n > 0
    return {"types": types_ok, "samples": samples}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Measure MIT component registries into the try-on catalog")
    ap.add_argument("--registry", default="all", help="registry id or 'all'")
    ap.add_argument("--style", default="base-nova", help="shadcn style (base-nova | new-york-v4)")
    ap.add_argument("--db", default=str(DB.DEFAULT_DB))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    roster = json.loads(ROSTER.read_text(encoding="utf-8"))
    regs = [r for r in roster["registries"] if r.get("status", "ok") == "ok"]
    if args.registry != "all":
        regs = [r for r in regs if r["id"] == args.registry]
        if not regs:
            print(f"no usable registry named {args.registry!r} (deferred/excluded/refused are not measurable)")
            return 2
    con = DB.connect(Path(args.db))
    run_start = DB.now()
    run_id = DB.reg_run_start(con, run_start, args.style)
    SNAPDIR.mkdir(parents=True, exist_ok=True)
    summary, failed, evidence = [], 0, {}
    tot_written = tot_skipped = 0
    for reg in regs:
        url = reg["index"].replace("{style}", args.style)
        try:
            raw = fetch(url)
            data = json.loads(raw)
            items = data.get("items") or []
        except Exception as e:  # one registry must never kill the run
            failed += 1
            summary.append({"registry": reg["id"], "ok": False, "error": f"{type(e).__name__}: {e}"})
            continue
        sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        # evidence is worth keeping, but a 2.4 MB index is not: compress anything over 512 KB
        raw_bytes = raw.encode("utf-8")
        if len(raw_bytes) > 512 * 1024:
            snap = SNAPDIR / f"{reg['id']}@{args.style}.json.gz"
            with gzip.open(snap, "wb") as fh:
                fh.write(raw_bytes)
            (SNAPDIR / f"{reg['id']}@{args.style}.json").unlink(missing_ok=True)  # drop a stale plain copy
        else:
            snap = SNAPDIR / f"{reg['id']}@{args.style}.json"
            snap.write_text(raw, encoding="utf-8")
            (SNAPDIR / f"{reg['id']}@{args.style}.json.gz").unlink(missing_ok=True)
        (SNAPDIR / f"{reg['id']}@{args.style}.meta.json").write_text(json.dumps(
            {"url": url, "sha256": sha, "bytes": len(raw.encode()), "file": snap.name,
             "gzip": snap.name.endswith(".gz"), "items": len(items),
             "fetched_at": DB.now(), "style": args.style}, indent=1), encoding="utf-8")
        recs = normalize(reg, args.style, items, url,
                         probe=(probe := probe_families(reg, args.style, items))["types"])
        evidence[reg["id"]] = {"probed_at": DB.now(), "style": args.style,
                               "types": probe["types"], "samples": probe["samples"][:12]}
        written = skipped = 0
        if DB.reg_run_is_stale(con, run_start):
            # per-row guards cannot see rows this run alone would touch: refuse the whole registry
            summary.append({"registry": reg["id"], "ok": True, "stale": True, "items": len(items),
                            "written": 0, "skipped": 0, "free": 0, "slotted": 0,
                            "families": probe["types"]})
            continue
        for rec in recs:
            st = DB.reg_upsert(con, rec, not_before=run_start)
            written += st == "written"
            skipped += st == "skipped-newer"
        tot_written += written
        tot_skipped += skipped
        summary.append({"registry": reg["id"], "ok": True, "sha256": sha[:12], "items": len(items),
                        "written": written, "skipped": skipped,
                        "free": sum(r["free"] for r in recs),
                        "families": probe["types"],
                        "slotted": sum(1 for r in recs if r["slot"])})
    slots = DB.reg_slots(con)
    thin = sorted({s["slot"] for s in slots if (s["n_free"] or 0) <= 3})
    DB.reg_run_finish(con, run_id, ",".join(r["id"] for r in regs), tot_written, tot_skipped)
    EVIDENCE.write_text(json.dumps({"style": args.style, "checked_at": DB.now(), "registries": evidence},
                                   indent=1, ensure_ascii=False), encoding="utf-8")
    stale = [s["registry"] for s in summary if s.get("stale")]
    out = {"ok": failed < len(regs), "style": args.style, "registries": summary, "evidence": str(EVIDENCE),
           "stale_refused": stale,
           "catalog": {"items": sum(s["n"] for s in slots), "slots": len(slots), "thin_slots": thin}}
    if args.json:
        print(json.dumps(out, indent=1))
    else:
        for s in summary:
            if s.get("stale"):
                print(f"  {s['registry']:<10} REFUSED — stale run: a newer completed intake exists")
            elif s.get("ok"):
                fam = " ".join(f"{t.split(':')[-1]}={'ok' if v else 'no'}" for t, v in s["families"].items())
                print(f"  {s['registry']:<10} {s['items']:>4} items  sha {s['sha256']}  "
                      f"free {s['free']:>4}  slotted {s['slotted']:>4}  (written {s['written']}, skipped {s['skipped']})  [{fam}]")
            else:
                print(f"  {s['registry']:<10} FAILED  {s['error']}")
        print(f"catalog: {out['catalog']['items']} items over {out['catalog']['slots']} slots; "
              f"thin (<=3 free): {', '.join(thin) or 'none'}")
    return 0 if failed < len(regs) else 3


if __name__ == "__main__":
    sys.exit(main())
