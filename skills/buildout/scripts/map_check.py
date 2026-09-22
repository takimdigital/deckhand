#!/usr/bin/env python3
"""map_check.py — the map completeness gate (buildout).

Validates a spec-mode / audit map directory against the gate:
    charters count == inventory count · zero silent blanks · zero dead-ends.

Depth-aware: `depth: lean|full` (first lines of summary.md). lean = the site's
edge registries must cover at least the 6 core categories; full = all 11.
Skips (exit 0) when the map directory does not exist — maps are graceful,
never mandatory (builds without a map behave exactly as before).

Usage: py scripts/map_check.py [--map <map-dir>] [--direction <direction-dir>] [--lock <path>] [--allow-missing a,b] [--json]
Exit:  0 pass or skip · 1 violations (refuses the freeze — fix the artifact, not the gate)
Each arm is skip-graceful: a missing map/direction directory prints SKIP (exit 0).
`--allow-missing` is the merge-time self-check escape (e.g. `--allow-missing pass2`
before PASS_2 exists) — the FREEZE run is strict.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

CORE6 = ["empty", "error", "loading_latency", "permission_role", "boundary", "interruption"]
FULL11 = CORE6 + ["state_conflict", "device_context", "unhappy_path", "lifecycle", "ai_agent"]

_COMMENTS = re.compile(r"<!--.*?-->", re.S)


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _plain(text: str) -> str:
    return _COMMENTS.sub("", text)


def _line_no(text: str, needle: str) -> int:
    for i, line in enumerate(text.splitlines(), 1):
        if needle in line:
            return i
    return 0


def _cells(s: str) -> list[str]:
    """Split a markdown table row into cells. A `\\|` inside a cell is an escaped
    pipe (the doc convention) and must NOT split the cell — it unescapes to `|`."""
    parts = re.split(r"(?<!\\)\|", s.strip().strip("|"))
    return [p.replace("\\|", "|").strip() for p in parts]


def check(map_dir: Path) -> list[tuple[str, str, str]]:
    """Return violations as (rule, file, detail); empty list = pass."""
    v: list[tuple[str, str, str]] = []

    # R1 — depth declared (sets the completeness bar)
    summary = map_dir / "summary.md"
    depth = None
    if not summary.is_file():
        v.append(("R1", "summary.md", "missing"))
    else:
        head = "\n".join(_read(summary).splitlines()[:6])
        m = re.search(r"depth:\s*(lean|full)", head)
        if m:
            depth = m.group(1)
        else:
            v.append(("R1", "summary.md", "no `depth: lean|full` in the first 5 lines"))
        if not re.search(r"map_version:\s*\d+", head):
            v.append(("R1", "summary.md", "no `map_version: <int>` in the first 5 lines"))
        for i, line in enumerate(_plain(_read(summary)).splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if re.search(r"<[A-Za-z0-9][^<>\n]{0,60}>", line):
                v.append(("R7", f"summary.md:{i}", "unfilled template placeholder"))
            elif "[STATUS]" in line:
                v.append(("R7", f"summary.md:{i}", "status tag not filled ([STATUS] left in)"))
            elif re.search(r"\b(TBD|TODO|FIXME|FILL_ME)\b", line):
                v.append(("R7", f"summary.md:{i}", "unresolved marker (TBD/TODO/FIXME/FILL_ME)"))

    # R2 — inventory: non-empty, every item names its source
    inv = map_dir / "inventory.md"
    items: list[str] = []
    if not inv.is_file():
        v.append(("R2", "inventory.md", "missing"))
    else:
        text = _plain(_read(inv))
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s.startswith("- "):
                continue
            body = s[2:].strip()
            item_id = re.split(r"[·|—]", body)[0].strip()
            items.append(item_id)
            if "source:" not in s:
                v.append(("R2", f"inventory.md:{i}", f"item `{item_id}` has no `source:`"))
        if not items:
            v.append(("R2", "inventory.md", "no items listed"))

    # R3 — charters count == inventory count (one charter per item, no orphans)
    cdir = map_dir / "charters"
    have = sorted(p.stem for p in cdir.glob("*.md")) if cdir.is_dir() else []
    missing = [i for i in items if i not in have]
    extra = [h for h in have if h not in items]
    if missing:
        v.append(("R3", "charters/", "no charter for: " + ", ".join(missing)))
    if extra:
        v.append(("R3", "charters/", "charter not in inventory: " + ", ".join(extra)))
    if items and not missing and not extra and len(have) != len(items):
        v.append(("R3", "charters/", f"count {len(have)} != inventory {len(items)}"))

    # R4 / R7 — charters: no silent blanks, no unfilled template placeholders
    for f in sorted(cdir.glob("*.md")) if cdir.is_dir() else []:
        rel = f.relative_to(map_dir)
        text = _plain(_read(f))
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("#"):
                continue
            # a bare `key:` at column 0 is a silent blank only when nothing follows
            # it (no indented block value, no table) — block keys like step_sequence
            # legitimately carry their value on following indented lines.
            if re.match(r"^[a-z_]+:\s*$", line):
                nxt = next((ln for ln in lines[i:] if ln.strip()), "")
                if not nxt.startswith((" ", "\t", "|")):
                    v.append(("R4", f"{rel}:{i}", f"silent blank: `{line.strip()}`"))
            if re.search(r"<[A-Za-z0-9][^<>\n]{0,60}>", line):
                v.append(("R7", f"{rel}:{i}", "unfilled template placeholder"))
            elif "[STATUS]" in line:
                v.append(("R7", f"{rel}:{i}", "status tag not filled ([STATUS] left in)"))
            elif re.search(r"\b(TBD|TODO|FIXME|FILL_ME)\b", line):
                v.append(("R7", f"{rel}:{i}", "unresolved marker (TBD/TODO/FIXME/FILL_ME)"))

    # R5 — flows: present, never merged, next_action non-empty, zero dead-ends
    fdir = map_dir / "flows"
    flow_files = sorted(fdir.glob("*.md")) if fdir.is_dir() else []
    if not flow_files:
        v.append(("R5", "flows/", "no flow maps"))
    for f in flow_files:
        rel = f.relative_to(map_dir)
        text = _plain(_read(f))
        if text.count("# FLOW_MAP:") > 1:
            v.append(("R5", str(rel), "merged flows — more than one FLOW_MAP header in one file"))
        for i, line in enumerate(text.splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            if re.search(r"<[A-Za-z0-9][^<>\n]{0,60}>", line):
                v.append(("R7", f"{rel}:{i}", "unfilled template placeholder"))
            elif "[STATUS]" in line:
                v.append(("R7", f"{rel}:{i}", "status tag not filled ([STATUS] left in)"))
            elif re.search(r"\b(TBD|TODO|FIXME|FILL_ME)\b", line):
                v.append(("R7", f"{rel}:{i}", "unresolved marker (TBD/TODO/FIXME/FILL_ME)"))
            m = re.search(r"next_action:\s*(.*)$", line)
            if m:
                val = m.group(1).strip()
                if not val or (val.startswith("<") and val.endswith(">")):
                    v.append(("R5", f"{rel}:{i}", "empty next_action (a planned dead end)"))
            m = re.match(r"^\s*dead_ends_found:\s*(.*)$", line)
            if m:
                val = m.group(1).strip().strip("[]").strip()
                if val and val.lower() not in ("none", "-", ""):
                    v.append(("R5", f"{rel}:{i}", f"dead_ends_found not empty: {val}"))

    # R6 — edge registries: bar per depth, no empty cells, no Y dead-ends
    edir = map_dir / "edges"
    edge_files = sorted(edir.glob("*.md")) if edir.is_dir() else []
    if not edge_files:
        v.append(("R6", "edges/", "no edge-case registries"))
    bar = FULL11 if depth == "full" else CORE6
    for f in edge_files:
        rel = f.relative_to(map_dir)
        text = _plain(_read(f))
        cats: list[str] = []
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if re.search(r"<[A-Za-z0-9][^<>\n]{0,60}>", s):
                v.append(("R7", f"{rel}:{i}", "unfilled template placeholder"))
            elif "[STATUS]" in s:
                v.append(("R7", f"{rel}:{i}", "status tag not filled ([STATUS] left in)"))
            elif re.search(r"\b(TBD|TODO|FIXME|FILL_ME)\b", s):
                v.append(("R7", f"{rel}:{i}", "unresolved marker (TBD/TODO/FIXME/FILL_ME)"))
            if not s.startswith("|"):
                continue
            cells = _cells(s)
            if not cells or all(c == "" for c in cells):
                continue
            first = cells[0].strip("`* ").lower()
            if first in ("category", "") or set(first) <= set("-: "):
                continue
            cat = re.split(r"\(", first)[0].strip()  # lifecycle(first/repeat/lapsed) -> lifecycle
            if cat not in FULL11:
                continue
            cats.append(cat)
            row_na = False
            for ci, cell in enumerate(cells[1:], 1):
                low = cell.lower()
                if not cell:
                    v.append(("R6", f"{rel}:{i}", f"empty cell in row `{cat}`"))
                elif ci == 1 and low.startswith("not_applicable"):
                    row_na = True  # the documented convention — a reasoned non-applicability
                elif ci == 1 and not low.startswith(("y", "n")):
                    v.append(("R6", f"{rel}:{i}", f"exists cell must be Y|N (or `not_applicable: reason`) in row `{cat}`"))
                elif ci == 3 and low.startswith("y") and not row_na:
                    v.append(("R6", f"{rel}:{i}", f"dead-end `Y` in row `{cat}` — design it out"))
        miss = [c for c in bar if c not in cats]
        if miss:
            v.append(("R6", str(rel), f"missing categories (depth {depth or '?'}): " + ", ".join(miss)))

    return v


LOCK_KEYS_TOP = ["version", "seed", "randomness", "vibes", "density", "radius", "motion",
                 "maxAnimatedPerPage", "colors", "fonts", "base"]
LOCK_KEYS_COLORS = ["background", "surface", "ink", "muted", "accent", "border"]
LOCK_KEYS_FONTS = ["display", "body", "mono", "license"]
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def check_direction(d: Path, lock_override: str | None = None, allowed_missing: set | None = None) -> list[tuple[str, str, str]]:
    """Direction-stage gate (ref 50): artifacts exist + forks/criteria + the merged lock's format.

    `allowed_missing` (merge-time self-check only): artifact names the caller
    explicitly allows to be absent (e.g. `pass2` before PASS_2 ran). The FREEZE
    run passes nothing — strict.
    """
    v: list[tuple[str, str, str]] = []
    am = {s if s.endswith(".md") else s + ".md" for s in (allowed_missing or set())}
    for name in ("A.md", "B.md", "forks.md", "final.md", "decision.md", "pass2.md", "log.md"):
        if name in am and not (d / name).is_file():
            continue
        if not (d / name).is_file():
            v.append(("D1", name, "missing"))

    fk = d / "forks.md"
    if fk.is_file():
        text = _plain(_read(fk))
        rows = 0
        bad_rows: list[int] = []
        for i, line in enumerate(text.splitlines(), 1):
            s = line.strip()
            if not s.startswith("|"):
                continue
            cells = _cells(s)
            if not cells or all(c == "" for c in cells):
                continue
            first = cells[0].strip("`* ").lower()
            if set(first) <= set("-: "):
                continue
            if first == "#" or "fork" in first:
                low = s.lower()
                if "criterion" not in low:
                    v.append(("D2", f"forks.md:{i}", "header has no `criterion` column (pre-committed criterion)"))
                if "cost" not in low:
                    v.append(("D2", f"forks.md:{i}", "header has no `cost` column"))
                continue
            if not re.match(r"^\d+$", first):
                continue
            rows += 1
            if len(cells) >= 8:
                if not cells[2]:
                    v.append(("D2", f"forks.md:{i}", "empty criterion cell"))
                if not cells[6]:
                    v.append(("D2", f"forks.md:{i}", "empty cost cell"))
                if not cells[7]:
                    v.append(("D2", f"forks.md:{i}", "empty resolution cell"))
                elif cells[7].strip().lower() in ("open", "tbd", "?"):
                    v.append(("D2", f"forks.md:{i}", f"unresolved resolution: {cells[7]}"))
            else:
                bad_rows.append(i)
        if bad_rows:
            v.append(("D2", f"forks.md:{bad_rows[0]}",
                      f"{len(bad_rows)} row(s) do not match the 8-column schema "
                      "(| # | fork | criterion | position A | position B | evidence | cost | resolution |)"))
        if rows == 0:
            v.append(("D2", "forks.md", "no fork rows"))
        elif rows > 5:
            v.append(("D2", "forks.md", f"{rows} forks — over the ~5 cap"))

    # D3 — exactly one LIVE final direction: one `winner:` declaration at the
    # START of a line (prose mentioning the winner must not count); any other
    # document declaring one must be annotated `retired`.
    win_re = re.compile(r"^\s*(?:\*\*)?winner\s*:", re.I | re.M)
    winners = []
    skip_d3 = "final.md" in am and not (d / "final.md").is_file()
    for f in sorted(d.glob("*.md")):
        if win_re.search(_plain(_read(f))):
            winners.append(f)
    if skip_d3:
        pass
    elif not winners:
        v.append(("D3", "final.md", "no `winner:` declaration at line start — the ONE direction must be named"))
    elif len(winners) > 1:
        if not any(f.name == "final.md" for f in winners):
            v.append(("D3", "final.md", "`winner:` declared elsewhere but not in final.md — the ONE live direction must be named there"))
        for f in winners:
            if f.name == "final.md":
                continue
            if "retired" not in _plain(_read(f)).lower():
                v.append(("D3", f.name, "second live direction — annotate `retired` (or remove)"))
    elif winners[0].name != "final.md":
        v.append(("D3", winners[0].name, "the `winner:` declaration lives in final.md"))

    dec = d / "decision.md"
    if dec.is_file() and "minority" not in _plain(_read(dec)).lower():
        v.append(("D4", "decision.md", "no minority report (losing option + reopening evidence)"))

    # D5 — PASS_2 must cite artifacts + locations, not verdicts
    p2 = d / "pass2.md"
    if p2.is_file():
        cites = re.findall(r"[A-Za-z0-9_.\-]+:\d+", _plain(_read(p2)))
        if len(cites) < 2:
            v.append(("D5", "pass2.md", "no artifact+location citations (need ≥2 like `brief:21` / `acceptance.md:6`)"))

    lg = d / "log.md"
    if lg.is_file():
        t = _plain(_read(lg)).lower()
        if "cost" not in t:
            v.append(("D6", "log.md", "no stage cost recorded"))
        if "vindication" not in t:
            v.append(("D6", "log.md", "no `vindication:` field"))
        # D8 — blinding witness: the host records each draft's sha256 at write
        # time; the scribe re-verifies both at merge start. Two 64-hex hashes,
        # or an explicit DEGRADED statement, must be in log.md.
        if len(re.findall(r"\b[0-9a-f]{64}\b", t)) < 2 and "degraded" not in t:
            v.append(("D8", "log.md", "no blinding witness — two draft sha256 hashes (or an explicit DEGRADED statement) required"))

    cands: list[Path] = []
    if lock_override:
        cands.append(Path(lock_override))
    cands += [d.parent / ".design" / "design.lock.json", d.parent / "design.lock.json", d / "design.lock.json"]
    lock = next((c for c in cands if c.is_file()), None)
    if lock is None:
        v.append(("D7", "design.lock.json", "no merged lock found (.design/design.lock.json, next to direction/, or inside it)"))
    else:
        try:
            data = json.loads(_read(lock))
        except Exception as e:  # noqa: BLE001
            v.append(("D7", lock.name, f"lock is not valid JSON: {e}"))
            data = None
        if isinstance(data, dict):
            for k in LOCK_KEYS_TOP:
                if k not in data:
                    v.append(("D7", lock.name, f"missing key `{k}` (ref-10 lock schema — no removed/renamed keys)"))
            colors = data.get("colors") if isinstance(data.get("colors"), dict) else {}
            for k in LOCK_KEYS_COLORS:
                if k not in colors:
                    v.append(("D7", lock.name, f"missing `colors.{k}`"))
                elif not HEX.match(str(colors[k])):
                    v.append(("D7", lock.name, f"`colors.{k}` is not a 6-hex value: {colors[k]}"))
            fonts = data.get("fonts") if isinstance(data.get("fonts"), dict) else {}
            for k in LOCK_KEYS_FONTS:
                if k not in fonts:
                    v.append(("D7", lock.name, f"missing `fonts.{k}`"))
            for key, allowed in (("randomness", ["safe", "coherent-random", "adventurous"]),
                                 ("density", ["compact", "comfortable", "airy"]),
                                 ("motion", ["none", "subtle", "medium"])):
                val = data.get(key)
                if val is not None and val not in allowed:
                    v.append(("D7", lock.name, f"`{key}` not in ref-10 vocabulary {allowed}: {val}"))
            if "seed" in data and not isinstance(data["seed"], int):
                v.append(("D7", lock.name, f"`seed` must be an int: {data['seed']!r}"))
            if "vibes" in data and not (isinstance(data["vibes"], list) and all(isinstance(x, str) for x in data["vibes"])):
                v.append(("D7", lock.name, "`vibes` must be a list of strings"))
            if "base" in data and (not isinstance(data["base"], str) or data["base"] not in ("radix", "none")):
                v.append(("D7", lock.name, f"`base` not in vocabulary ['radix','none']: {data.get('base')!r}"))
            if "dark" in data:
                dk = data["dark"]
                if not isinstance(dk, dict):
                    v.append(("D7", lock.name, "`dark` must be an object carrying the six color keys"))
                else:
                    for k in LOCK_KEYS_COLORS:
                        if k not in dk or not HEX.match(str(dk.get(k))):
                            v.append(("D7", lock.name, f"`dark.{k}` missing or not 6-hex: {dk.get(k)!r}"))
            if "focus_ring" in data and not HEX.match(str(data.get("focus_ring"))):
                v.append(("D7", lock.name, f"`focus_ring` must be a 6-hex color: {data.get('focus_ring')!r}"))
    return v


def count_add_rows(map_dir: Path) -> int:
    """Lines carrying the `ADD` tag (checks the map adds beyond the brief) —
    informational for the verify stage, which must turn each into a row."""
    n = 0
    for f in sorted(map_dir.rglob("*.md")):
        for line in _plain(_read(f)).splitlines():
            if re.search(r"\bADD\b", line):
                n += 1
    return n


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Freeze gate: map completeness (charters==inventory, no silent blanks, no dead-ends) + direction artifacts + merged lock format.")
    ap.add_argument("--map", default=None, dest="map_dir", help="path to the map/ directory (optional arm)")
    ap.add_argument("--direction", default=None, dest="direction_dir", help="path to the direction/ directory (optional arm)")
    ap.add_argument("--lock", default=None, help="explicit path to the merged design.lock.json (default: derived from --direction)")
    ap.add_argument("--allow-missing", default="", dest="allow_missing",
                    help="comma list of direction artifacts allowed to be missing (merge-time self-check only — the FREEZE run is strict)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args(argv)
    if not a.map_dir and not a.direction_dir:
        print("nothing to check: give --map and/or --direction")
        return 2

    v: list[tuple[str, str, str]] = []
    msgs: list[str] = []
    arms_ran = False
    if a.map_dir:
        md = Path(a.map_dir)
        if md.is_dir():
            arms_ran = True
            v += check(md)
        else:
            msgs.append(f"SKIP: no map at {md.resolve()} - building directly (not an error; --map/--direction resolve from the current directory - run the gate from the project root)")
    if a.direction_dir:
        dd = Path(a.direction_dir)
        if dd.is_dir():
            arms_ran = True
            allow = {s.strip() for s in a.allow_missing.split(",") if s.strip()}
            v += check_direction(dd, a.lock, allow)
        else:
            msgs.append(f"SKIP: no direction at {dd.resolve()} - single-designer path (not an error; --map/--direction resolve from the current directory - run the gate from the project root)")

    for m in msgs:
        print(m)
    if a.json:
        status = "fail" if v else ("pass" if arms_ran else "skip")
        print(json.dumps({"status": status, "messages": msgs,
                          "violations": [{"rule": r, "file": f, "detail": t} for r, f, t in v]}, indent=2))
    elif v:
        print(f"GATE: FAIL - {len(v)} violation(s):")
        for r, f, t in v:
            print(f"  {r} | {f} | {t}")
    elif not arms_ran:
        pass  # SKIP message already printed — graceful, exit 0
    elif a.map_dir and not a.direction_dir:
        print("MAP GATE: PASS - charters == inventory, no silent blanks, no dead-ends")
        n_add = count_add_rows(Path(a.map_dir))
        if n_add:
            print(f"ADD rows: {n_add} (the verify ref must turn EACH into an acceptance check)")
    else:
        print("GATE: PASS" + ("" if not msgs else " (with skips)"))
    return 1 if v else 0


if __name__ == "__main__":
    sys.exit(main())
