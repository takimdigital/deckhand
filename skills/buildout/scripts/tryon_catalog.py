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


def _row_get(row, key, default=None):
    """One field of a catalog row — callers pass both dicts and sqlite3.Rows."""
    try:
        val = row[key]
    except (KeyError, IndexError, TypeError):
        return default
    return default if val is None else val


def row_type(row) -> str:
    return _row_get(row, "type", "") or ""


def split_examples(rows):
    """`(kept, hidden_examples)` — the demo split every picker runs (F4).

    A `registry:example` row is a default-export, fixed-content wrapper: it passes every structural
    check while destroying the owner's content, and 202/454 measured Radix offers were demos. A
    picker keeps `kept` by default; `hidden_examples` is returned so the caller can COUNT it
    (`scope.hidden_demos`) and offer the real component the demo names — hidden, never dropped.
    """
    kept, hidden = [], []
    for r in rows:
        (hidden if row_type(r) == "registry:example" else kept).append(r)
    return kept, hidden


def registry_deps(row) -> list[str]:
    """The row's registryDependencies as item names (the column holds JSON text)."""
    try:
        deps = json.loads(_row_get(row, "registry_deps", "") or "[]")
    except Exception:
        return []
    return [d for d in deps if isinstance(d, str)] if isinstance(deps, list) else []


def promote_examples(hidden_examples, pool, taken=()):
    """The real component behind each hidden demo (F4) — measured: 19/19 sampled demos name it.

    For every hidden example take the FIRST `registry_deps` name that has a row of the SAME slot in
    the SAME registry inside `pool` — the pool is already base-filtered, so a promoted row can never
    break the hard base filter. A demo is never a promotion target (it would be hidden too), and any
    key in `taken` (what the picker already shows) or already promoted is skipped, so a component
    that is both offered and named by a demo appears exactly once.
    """
    offerable: dict[tuple[str, str], dict] = {}
    for r in pool:
        if row_type(r) == "registry:example":
            continue
        offerable.setdefault((_row_get(r, "registry", ""), _row_get(r, "item", "")), r)
    out, seen = [], set(taken)
    for ex in hidden_examples:
        reg, slot = _row_get(ex, "registry", ""), _row_get(ex, "slot", "")
        for dep in registry_deps(ex):
            hit = offerable.get((reg, dep))
            if hit is None or _row_get(hit, "slot", "") != slot:
                continue
            if (reg, dep) not in seen:
                seen.add((reg, dep))
                out.append(hit)
            break                      # only the demo's FIRST offerable dep is promoted
    return out


PROMOTED_WHY = "promoted:demo-dep"     # provenance tag: this row is here because a hidden demo names it


def rank_key(sc: int, row: dict, pref: str | None = None):
    """The ONE ordering rule: the owner's own rows, then the project's registry lineage, then score,
    then a stable registry/item order."""
    return (0 if row["registry"] == "mine" else (1 if (pref and row["registry"] == pref) else 2),
            -sc, row["registry"], row["item"])


def _rank(rows_, slot: str, base: str | None, pref: str | None):
    """Score (`score`) + sort (`rank_key`) — the only ranking path there is, for every picker row."""
    out = []
    for r in rows_:
        sc, why = score(r, slot, base)
        if sc > 0:
            out.append((sc, why, r))
    out.sort(key=lambda t: rank_key(t[0], t[2], pref))
    return out


def picker_rows(pool, slot: str, base: str | None, top: int,
                include_examples: bool = False, pref: str | None = None):
    """The rows a picker shows: `([(score, why, row)], hidden_demos)`.

    Demos are out of the default list — counted as `hidden_demos`, never silently dropped — and the
    real component each hidden demo names is promoted into their place (deduped, ranked through the
    same score/sort path as every other row). With `include_examples` the demos themselves stay on
    the list instead. The CLI and the helper's `/catalog` both call THIS, so they cannot drift.
    """
    kept, demos = split_examples(pool)
    window = _rank(kept, slot, base, pref)[:top]
    if include_examples:
        # the demos the owner explicitly asked for: listed after the offers window, in rank order —
        # a window that cut them off again would make the flag a no-op on exactly the slots this
        # task fixes (measured: all 36 button/radix demos rank below 21 real components)
        return window + _rank(demos, slot, base, pref), 0
    shown = {(_row_get(r, "registry", ""), _row_get(r, "item", "")) for _sc, _why, r in window}
    extra = []
    for r in promote_examples(demos, pool, taken=shown):
        # a row the window cut (or the sc>0 rule dropped) but a hidden demo names: it is not
        # "already present", so it is promoted — scored by the same `score`, sorted by the same key
        sc, why = score(r, slot, base)
        extra.append((sc, why + [PROMOTED_WHY], r))
    extra.sort(key=lambda t: rank_key(t[0], t[2], pref))
    return window + extra, len(demos)


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
    # demos (`registry:example`) are OUT of the default picker and COUNTED, never silently dropped
    # (F4); the real component each hidden demo names is promoted in its place. One shared path with
    # the helper's /catalog — `picker_rows` owns the split, the promotion and the ranking key.
    shown_rows, hidden_demos = picker_rows(rows, args.slot, base, args.top,
                                           include_examples=args.include_examples, pref=pref)
    if args.json:
        print(json.dumps([{"score": sc, "why": why, **r} for sc, why, r in shown_rows], indent=1))
    else:
        style = prof.get("shadcn_item_style", "base-nova")
        scope_bits = [f"base {base or 'unknown'}"]
        if prof.get("lineage"):
            scope_bits.append(prof["lineage"])
        if args.registry:
            scope_bits.append(f"registry {args.registry}")
        demos_shown = sum(1 for _sc, _why, r in shown_rows if row_type(r) == "registry:example")
        demos_bit = f"; {hidden_demos} demos hidden" if hidden_demos else \
            (f"; {demos_shown} demos shown (registry:example, not offers)" if demos_shown else "")
        print(f"slot: {args.slot}  (scope: {' · '.join(scope_bits)})"
              f"  [#{len(shown_rows)} of {len(all_rows)} live items"
              + (f"; {hidden} hidden (need {', '.join(b for b in hidden_bases if b)})" if hidden else "")
              + demos_bit + "]")
        for sc, why, r in shown_rows:
            url = r["item_url"]
            if r["registry"] == "shadcn":
                url = url.replace("/{style}/", f"/{style}/" if "{style}" in url else "/")
            gate = "" if r["free"] else "  [gated]"
            if PROMOTED_WHY in why:
                gate += "  [promoted: the demo it stands in for is hidden]"
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
    p.add_argument("--include-examples", action="store_true",
                   help="also list registry:example demos (demos are never offers — they carry "
                        "fixed demo content; listed after the offers, in the same rank order)")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("project")
    p.add_argument("--project", required=True)
    args = ap.parse_args(argv)
    con = DB.connect_catalog(Path(args.db))
    return {"slots": cmd_slots, "query": cmd_query, "project": cmd_project}[args.cmd](con, args)


if __name__ == "__main__":
    sys.exit(main())
