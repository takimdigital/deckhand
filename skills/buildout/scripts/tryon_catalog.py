#!/usr/bin/env python3
"""tryon_catalog — deterministic queries against the measured component registry.

    py scripts/tryon_catalog.py slots                          # every slot with counts
    py scripts/tryon_catalog.py query --slot button            # ranked candidates
    py scripts/tryon_catalog.py query --slot button --base base-ui --top 5 --json
    py scripts/tryon_catalog.py project --project D:/app       # what base/style is this project?

Ranking is a script run, never an opinion: keyword hit in the item name beats title beats
categories beats description; a base match adds; shadcn wins ties (source of truth).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import templates_db as DB

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
ROSTER = SKILL / "data" / "registries.json"


def project_profile(project: Path) -> dict:
    """Read the target project: shadcn style/base + package manager hints. Never guesses silently."""
    prof = {"project": str(project), "style": None, "base": None, "lineage": None, "evidence": []}
    cj = project / "components.json"
    if cj.exists():
        try:
            cfg = json.loads(cj.read_text(encoding="utf-8"))
            prof["style"] = (cfg.get("style") or "").strip() or None
            if "ui.shadcn.com" in str(cfg.get("$schema") or "") or prof["style"]:
                prof["lineage"] = "shadcn-style"
            prof["evidence"].append(f"components.json style={prof['style']}")
        except Exception as e:
            prof["evidence"].append(f"components.json unreadable: {e}")
    pkg = project / "package.json"
    deps: dict = {}
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))          # read ONCE
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        except Exception:
            pass
    if any(d.startswith("@base-ui") for d in deps):
        prof["base"] = "base-ui"
        prof["evidence"].append("package.json has @base-ui")
    elif any(d == "radix-ui" or d.startswith("@radix-ui") for d in deps):
        prof["base"] = "radix"
        prof["evidence"].append("package.json has radix-ui")
    if not prof["base"] and prof["style"]:
        prof["base"] = "base-ui" if prof["style"].startswith("base") else "radix"
        prof["evidence"].append(f"base inferred from style {prof['style']}")
    if deps and not prof["base"]:
        prof["base"] = "none"
    style = prof["style"] or "base-nova"
    prof["shadcn_item_style"] = style
    return prof


def score(row: dict, slot: str, base: str | None) -> tuple[int, list[str]]:
    s, why = 0, []
    name = (row.get("item") or "").lower()
    title = (row.get("title") or "").lower()
    cats = " ".join(json.loads(row.get("categories") or "[]")).lower() if row.get("categories") else ""
    desc = (row.get("description") or "").lower()
    pat = r"(?<![a-z0-9])" + re.escape(slot)
    if re.search(pat, name):
        s += 100
        why.append("name")
    if re.search(pat, title):
        s += 60
        why.append("title")
    if re.search(pat, cats):
        s += 40
        why.append("categories")
    if re.search(pat, desc):
        s += 30
        why.append("description")
    if (row.get("type") or "") in ("registry:ui", "registry:component"):
        s += 25                     # a real component outranks a registry:example demo file
        why.append("component")
    rb = row.get("base") or "none"
    if base:
        if rb == base:
            s += 15
            why.append(f"base:{base}")
        elif rb != "none" and rb != base:
            s -= 25
            why.append(f"base-mismatch:{rb}")
    # no blanket shadcn bonus: registry preference is an ORDERING rule in cmd_query / the server,
    # never a score that lets one registry outrank another on equal metadata
    return s, why


def cmd_slots(con, args) -> int:
    rows = DB.reg_slots(con)
    if args.need:
        rows = [r for r in rows if r["slot"] == args.need]
    if args.json:
        print(json.dumps(rows, indent=1))
    else:
        for r in rows:
            flag = "  thin" if (r["n_free"] or 0) <= 3 else ""
            print(f"  {r['slot']:<14} {r['slot_kind']:<9} free {r['n_free']:>3}/{r['n']:<3}{flag}")
    return 0


def cmd_query(con, args) -> int:
    base = args.base
    prof = project_profile(Path(args.project)) if args.project else {}
    if base is None:
        base = prof.get("base")
    # HARD base filter: a project never gets candidates that need a different primitive base
    # (reg_rows treats "same base or base-free" as compatible). Hidden ones are counted, not shown.
    all_rows = [dict(r) for r in DB.reg_rows(con, slot=args.slot, registry=args.registry,
                                             base=None, free_only=not args.include_gated)]
    filt = base if base in ("radix", "base-ui", "aria", "none") else None
    rows = [dict(r) for r in DB.reg_rows(con, slot=args.slot, registry=args.registry,
                                         base=filt, free_only=not args.include_gated)]
    hidden = len(all_rows) - len(rows)
    hidden_bases = sorted({r["base"] for r in all_rows} - {r["base"] for r in rows})
    pref = "shadcn" if prof.get("lineage") == "shadcn-style" else None
    ranked = []
    for r in rows:
        sc, why = score(r, args.slot, base)
        if sc > 0:
            ranked.append((sc, why, r))
    # the project's own registry lineage comes FIRST (keyword scores here measure metadata
    # completeness as much as fit — a sparse-title shadcn item must not lose to a chatty one),
    # then score, then a stable registry/item order
    # the owner's OWN saved components come first (pre-vetted by him; still under the same base
    # filter), then the project's own registry lineage, then score, then a stable registry/item order
    ranked.sort(key=lambda t: (0 if t[2]["registry"] == "mine" else
                               (1 if (pref and t[2]["registry"] == pref) else 2),
                               -t[0], t[2]["registry"], t[2]["item"]))
    ranked = ranked[: args.top]
    if args.json:
        print(json.dumps([{"score": sc, "why": why, **r} for sc, why, r in ranked], indent=1))
    else:
        style = prof.get("shadcn_item_style", "base-nova")
        scope_bits = [f"base {base or 'unknown'}"]
        if prof.get("lineage"):
            scope_bits.append(prof["lineage"])
        if args.registry:
            scope_bits.append(f"registry {args.registry}")
        print(f"slot: {args.slot}  (scope: {' · '.join(scope_bits)})"
              f"  [#{len(ranked)} of {len(all_rows)} live items"
              + (f"; {hidden} hidden (need {', '.join(b for b in hidden_bases if b)})" if hidden else "") + "]")
        for sc, why, r in ranked:
            url = r["item_url"]
            if r["registry"] == "shadcn":
                url = url.replace("/{style}/", f"/{style}/" if "{style}" in url else "/")
            gate = "" if r["free"] else "  [gated]"
            print(f"  {sc:>4}  {r['registry']:<10} {r['item']:<28} {r['type']:<20} "
                  f"base={r['base']:<8}{gate}")
            print(f"        {r['item_url']}")
            print(f"        npx shadcn@latest add \"{r['item_url']}\" --dry-run")
    return 0


def cmd_project(con, args) -> int:
    prof = project_profile(Path(args.project))
    print(json.dumps(prof, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Query the measured component registry (try-on)")
    ap.add_argument("--db", default=str(DB.DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("slots")
    p.add_argument("--need")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("query")
    p.add_argument("--slot", required=True)
    p.add_argument("--base", choices=["base-ui", "radix", "aria", "none"])
    p.add_argument("--registry", help="optional: restrict to one registry (preference is automatic)")
    p.add_argument("--project")
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--include-gated", action="store_true")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("project")
    p.add_argument("--project", required=True)
    args = ap.parse_args(argv)
    con = DB.connect(Path(args.db))
    return {"slots": cmd_slots, "query": cmd_query, "project": cmd_project}[args.cmd](con, args)


if __name__ == "__main__":
    sys.exit(main())
