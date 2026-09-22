#!/usr/bin/env python3
"""assemble_pick.py - deterministic, seeded, coherence-aware component picker.

Reads data/items/*.jsonl (+ overrides.jsonl), applies optional design.lock.json
constraints, and returns top-K candidates weighted by section/tag fit and
registry variety, sampled WITHOUT replacement via a seeded RNG
(Efraimidis-Spirakis weighted keys). Same seed + same inputs => same output.

Relevance model:
- Curated items (have `section`): match on section (+ `any` generalists, which must
  clear the relevance floor: >=1 requested-tag hit or the section keyword in
  name/title/description/tags).
- Uncurated items (no `section`): pass only when the requested tags - or the
  section name itself when no tags are given - appear in name/title/description.

Usage:
  py scripts/assemble_pick.py --section hero --tags animated,glow --k 3 --seed 4242
  py scripts/assemble_pick.py --section pricing --k 3 --seed 7 --lock <project>/design.lock.json --list
  py scripts/assemble_pick.py --section hero --tags <tag> --k 3 --seed 7 --explain

Honesty (stderr, never blocks): zero tag hits across the picks -> NO TAG MATCH
warning; a section with no curated rows -> the documented keyword-fallback line.
Picks are PROPOSALS - the lock and the client's bans decide.
"""
import argparse, glob, json, random, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ITEMS = str(ROOT / "data" / "items" / "*.jsonl")
OVERRIDES = ROOT / "data" / "items" / "overrides.jsonl"

def load_items(patterns, overrides_path=OVERRIDES):
    items = {}
    for pat in patterns:
        matches = sorted(glob.glob(pat))
        if not matches:
            raise FileNotFoundError(f"no item files matched {pat!r} - check the --items glob")
        for fp in matches:
            p = Path(fp)
            if p.name == "overrides.jsonl":
                continue
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    d = json.loads(line)
                    items[d["id"]] = d
    if overrides_path and Path(overrides_path).exists():
        for line in Path(overrides_path).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            ov = json.loads(line)
            if ov.get("id") in items:
                items[ov["id"]].update({k: v for k, v in ov.items() if k != "id"})
    return [items[k] for k in sorted(items)]

def _used_registries(lock):
    out = set()
    for v in (lock or {}).get("sections", {}).values():
        if isinstance(v, dict) and v.get("registry"):
            out.add(v["registry"])
    return out

def _text(item):
    return " ".join(str(item.get(k) or "") for k in ("name", "title", "description")).lower()

def passes(item, section, tags, lock, allow_unthemed):
    if item.get("themeable") is False and not allow_unthemed:
        return False
    secs = item.get("section") or []
    if secs:
        if section not in secs and "any" not in secs:
            return False
        if section not in secs:
            # relevance floor (field-test fix): an `any` generalist only counts when
            # it reflects at least one requested tag — or the section keyword itself.
            terms = [t.lower() for t in (tags or []) if t] or [section.lower()]
            hay = _text(item) + " " + " ".join(str(x).lower() for x in (item.get("tags") or []))
            if not any(term and term in hay for term in terms):
                return False
    else:
        terms = [t.lower() for t in (tags or []) if t] or [section.lower()]
        text = _text(item)
        if not any(term and term in text for term in terms):
            return False
    motion = (lock or {}).get("motion", "medium")
    if motion in ("none", "subtle") and "heavy-motion" in (item.get("tags") or []):
        return False
    return True

def score(item, section, tags, used):
    s = 0.0
    if section in (item.get("section") or []):
        s += 3.0
    s += 1.2 * len(set(tags) & set(item.get("tags") or []))
    if not (item.get("section") or []):
        text = _text(item)
        s += 0.5 * sum(1 for t in (list(tags) or [section]) if t and t.lower() in text)
    if item.get("registry") and item["registry"] not in used:
        s += 0.8
    sk = item.get("size_kb")
    if isinstance(sk, (int, float)):
        s -= min(float(sk), 50.0) / 100.0
    return max(s, 0.05)

def pick(items, section, tags, k, seed, lock=None, allow_unthemed=False):
    tags = [t for t in (tags or []) if t]
    used = _used_registries(lock)
    pool = [it for it in items if passes(it, section, tags, lock, allow_unthemed)]
    rnd = random.Random(seed)
    keyed = []
    for it in pool:
        w = score(it, section, tags, used)
        keyed.append((rnd.random() ** (1.0 / w), it))
    keyed.sort(key=lambda kv: kv[0], reverse=True)
    out = []
    for _, it in keyed[:k]:
        why = []
        if section in (it.get("section") or []):
            why.append("section")
        why += [f"tag:{t}" for t in sorted(set(tags) & set(it.get("tags") or []))]
        if not (it.get("section") or []) and any(t and t.lower() in _text(it) for t in (list(tags) or [section])):
            why.append("text-match")
        if it.get("registry") and it["registry"] not in used:
            why.append("fresh-registry")
        out.append({"id": it["id"], "name": it.get("title") or it["name"],
                    "registry": it.get("registry"), "install": it.get("install"), "why": why})
    return out

def warnings_for(picks, section, tags, items):
    """Loud honesty lines for a pick result (the CLI prints them to stderr):
    - zero tag hits across the picks: the tags did NOT drive this pick
    - no curated rows for the section in the whole pool: keyword fallback applies
    """
    out = []
    tags = [t for t in (tags or []) if t]
    if tags and picks and not any(w.startswith("tag:") for p in picks for w in p.get("why", [])):
        out.append("NO TAG MATCH - none of the picks matched tags " + ",".join(tags) +
                   "; they are section/registry-variety candidates only. Re-pick with fitting tags, curate overrides, or treat the zero-hit as evidence for the banlist override.")
    if not any(section in (it.get("section") or []) for it in items):
        out.append(f"no curated items for section '{section}' in the pool - documented fallback: search by keyword/tags instead (e.g. --section {section} --tags <keyword> --list), then `verify --item` before installing. Fallback candidates must clear the relevance floor: >=1 keyword/tag hit; if nothing clears it, hand-build the section from lock tokens instead of shipping an irrelevant component.")
    return out

def main():
    ap_ = argparse.ArgumentParser(description="seeded coherent component picker")
    ap_.add_argument("--section", required=True)
    ap_.add_argument("--tags", default="")
    ap_.add_argument("--k", type=int, default=3)
    ap_.add_argument("--seed", type=int, default=0)
    ap_.add_argument("--items", action="append", help="glob(s); default data/items/*.jsonl")
    ap_.add_argument("--lock", default=None, help="path to design.lock.json")
    ap_.add_argument("--allow-unthemed", action="store_true")
    ap_.add_argument("--list", action="store_true", help="list filtered pool instead of sampling")
    ap_.add_argument("--explain", action="store_true", help="print per-pick reasoning to stderr")
    args = ap_.parse_args()
    try:
        items = load_items(args.items or [DEFAULT_ITEMS])
    except FileNotFoundError as err:
        print(str(err))
        return 2
    lock = json.loads(Path(args.lock).read_text(encoding="utf-8")) if args.lock else None
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.list:
        pool = [it for it in items if passes(it, args.section, tags, lock, args.allow_unthemed)]
        for it in sorted(pool, key=lambda i: i["id"])[:50]:
            print(it["id"])
        print(f"({len(pool)} candidates)")
        if not any(args.section in (it.get("section") or []) for it in items):
            print(f"warning: no curated items for section '{args.section}' in the pool - documented fallback: search by keyword/tags instead; candidates above are text/section-name matches only and must clear the relevance floor (>=1 keyword/tag hit), `verify --item` before installing", file=sys.stderr)
        return 0
    picks = pick(items, args.section, tags, args.k, args.seed, lock, args.allow_unthemed)
    for w in warnings_for(picks, args.section, tags, items):
        print("warning: " + w, file=sys.stderr)
    if args.explain:
        by_id = {it["id"]: it for it in items}
        used = _used_registries(lock)
        for p in picks:
            it = by_id.get(p["id"], {})
            hits = sorted(set(tags) & set(it.get("tags") or []))
            sec = args.section in (it.get("section") or [])
            fresh = bool(it.get("registry")) and it["registry"] not in used
            print(f"explain {p['id']}: section-hit={sec} tag-hits={hits or '-'} fresh-registry={fresh} why={p['why']}", file=sys.stderr)
    print(json.dumps(picks, indent=1, ensure_ascii=False))
    return 0 if picks else 2

if __name__ == "__main__":
    sys.exit(main())
