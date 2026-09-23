#!/usr/bin/env python3
"""swap_check.py — prove the vendor dependencies are gone and the adapters are in.

Reads the project's .factory/swap-map.json (written by factory_clone.py from the
registry row) and scans the project for vendor SDK usage and required adapters.

usage:
  py scripts/swap_check.py --project D:/my-app [--map D:/my-app/.factory/swap-map.json] [--json]

exit 0 = all swaps verified · 1 = at least one swap incomplete · 2 = map/project missing
        3 = the map is EMPTY (nothing to verify is not a pass)
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

# .factory holds THIS check's own map — the map quotes the vendor patterns it is checking, so
# counting it as "vendor code left in the project" made exit 0 structurally unreachable.
SKIP_DIRS = {"node_modules", ".next", "dist", "build", ".git", ".turbo", "coverage",
             ".vercel", "__pycache__", ".venv", "venv", "out", ".factory"}
SKIP_FILES = {"pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lockb", "bun.lock"}
TEXT_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".py", ".css", ".md",
            ".env", ".example", ".yml", ".yaml", ".toml", ".prisma", ".sql", ".sh"}


def iter_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.name in SKIP_FILES:
            continue
        if p.suffix.lower() not in TEXT_EXT and p.name != "Dockerfile" and p.name != ".env.example":
            continue
        yield p


def _needle_hit(needle: str, line_low: str) -> bool:
    """Substring for SDK-shaped patterns ('@clerk/'); whole token for plain words.

    Bare words must never match inside another word (`ably` matched "pro**bably**" in a README, `pg`
    would match "jpg"), yet env-var names must still hit: `NEXT_PUBLIC_CLERK_KEY` must match `clerk`,
    so `_` splits tokens.
    """
    if re.search(r"[^a-z0-9]", needle):     # symbols in the pattern → plain substring
        return needle in line_low
    return needle in re.split(r"[^a-z0-9]+", line_low)


def scan(root: Path, patterns: list[str]) -> list[tuple[str, str, str]]:
    """Return [(relpath, pattern, line)] for every pattern hit outside node_modules."""
    hits: list[tuple[str, str, str]] = []
    needles = [p.lower() for p in patterns if p]
    if not needles:
        return hits
    for p in iter_files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        low = text.lower()
        if not any(n in low for n in needles):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            ll = line.lower()
            for n in needles:
                if _needle_hit(n, ll):
                    hits.append((str(p.relative_to(root)), n, line.strip()[:160]))
    return hits


def grep_present(root: Path, patterns: list[str], allow_globs: list[str]) -> dict:
    """For 'must be absent' patterns: hits that are NOT covered by an allow glob."""
    out = {"hits": [], "allowed": []}
    for rel, pat, line in scan(root, patterns):
        if any(fnmatch.fnmatch(rel, g) for g in allow_globs):
            out["allowed"].append({"file": rel, "pattern": pat, "line": line})
        else:
            out["hits"].append({"file": rel, "pattern": pat, "line": line})
    return out


ADAPTER_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".rb", ".go", ".php"}


def must_present(root: Path, patterns: list[str]) -> dict:
    """For 'must exist' patterns (the adapter): ANY of the alternatives counts (or package.json).

    The patterns are real identifiers from the vendor table's target column (e.g. both
    `socket.io` and `eventsource` for the realtime target) — prose like "socket.io-or-sse"
    or "middleware or none" is never used as a needle; those become removal-mode entries.

    An adapter is CODE or a dependency: only source files (and package.json) count. Measured false
    positive: `.oxlintrc.json` lists the browser global `EventSource`, which made an unswapped
    realtime entry report "adapter present".
    """
    res = {"hits": [], "in_package_json": []}
    pkg = root / "package.json"
    pkg_text = pkg.read_text(encoding="utf-8", errors="ignore").lower() if pkg.exists() else ""
    for pat in patterns:
        p = str(pat).lower()
        if pkg_text and p in pkg_text:
            res["in_package_json"].append(pat)
        res["hits"] += [{"file": r, "pattern": pa} for r, pa, _ in scan(root, [pat])
                        if Path(r).suffix.lower() in ADAPTER_EXT or Path(r).name == "package.json"]
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="verify vendor->open-source swaps in a cloned project")
    ap.add_argument("--project", required=True)
    ap.add_argument("--map", default=None, help="default: <project>/.factory/swap-map.json")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.project)
    if not root.is_dir():
        print(f"swap_check: project not found: {root}", file=sys.stderr)
        return 2
    map_path = Path(args.map) if args.map else root / ".factory" / "swap-map.json"
    if not map_path.exists():
        print(f"swap_check: swap map not found: {map_path}", file=sys.stderr)
        return 2
    data = json.loads(map_path.read_text(encoding="utf-8"))
    entries = data.get("swaps", data if isinstance(data, list) else [])
    if isinstance(entries, dict):  # {vendor: entry} is also accepted
        entries = list(entries.values())
    entries = [e for e in entries if isinstance(e, dict)]
    empty_map = not entries
    if empty_map:
        print(f"swap_check: {map_path} has no entries — NOTHING-TO-VERIFY IS NOT A PASS.\n"
              "  An empty map proves nothing: it is built from the registry row's measured vendor\n"
              "  deps, so a `--repo` clone (no registry row) starts empty even when the template\n"
              "  leans on vendors. Fix it at the source, then re-run:\n"
              "    py scripts/template_intake.py --repo <owner/name>   # measures licence/stack/vendors\n"
              "    py scripts/factory_clone.py --template <name> --slug <slug> --root <root>   # rebuilds the map\n"
              "  or hand-add entries to the map (vendor · patterns · target_patterns · status).")
        return 3

    results = []
    failed = 0
    for e in entries:
        vendor = e.get("vendor") or "?"
        target = e.get("target") or "?"
        status = e.get("status") or "pending"
        if status == "keep":
            results.append({"vendor": vendor, "target": "(kept)", "vendor_hits": [],
                            "adapter": {"hits": [], "in_package_json": []}, "verdict": "KEPT"})
            continue
        absent = grep_present(root, e.get("patterns") or [vendor], e.get("allow") or [])
        # Some documented targets are the owner's OWN code (db-backed flags, app middleware) or an
        # allowed deletion ("glitchtip or none") — there is no library to require. For those the
        # gate proves ABSENCE only; the choice itself is recorded in the entry's status.
        removal = str(status).lower() in ("removed", "own-code", "none") or \
            str(target).strip().lower() in ("none", "(removed)", "removed")
        if removal:
            adapter = {"hits": [], "in_package_json": []}
            ok = not absent["hits"]
        else:
            adapter = must_present(root, e.get("target_patterns") or [target])
            ok = not absent["hits"] and bool(adapter["hits"] or adapter["in_package_json"])
        if not ok:
            failed += 1
        results.append({
            "vendor": vendor, "target": target, "status": status, "removal_mode": removal,
            "vendor_hits": absent["hits"][:12], "vendor_hits_total": len(absent["hits"]),
            "allowed_hits": absent["allowed"][:6],
            "adapter": {"in_package_json": adapter["in_package_json"],
                        "files": sorted({h["file"] for h in adapter["hits"]})[:8]},
            "verdict": (("REMOVED" if removal else "OK") if ok else "INCOMPLETE"),
        })

    if args.json:
        print(json.dumps({"project": str(root), "map": str(map_path), "results": results,
                          "failed": failed}, ensure_ascii=False, indent=2))
    else:
        print(f"swap check — {root}")
        for r in results:
            print(f"  [{r['verdict']:10}] {r['vendor']:20} -> {r['target']}")
            if r["verdict"] == "OK":
                print(f"        adapter present: {', '.join(r['adapter']['in_package_json']) or r['adapter']['files'][:3]}")
            elif r["verdict"] == "REMOVED":
                print("        vendor gone; no replacement library required (decision recorded in the map)")
            elif r["verdict"] == "INCOMPLETE":
                if r["vendor_hits"]:
                    print(f"        {r['vendor_hits_total']} vendor reference(s) left, e.g. "
                          f"{r['vendor_hits'][0]['file']}: {r['vendor_hits'][0]['line'][:80]}")
                if not (r["adapter"]["in_package_json"] or r["adapter"]["files"]):
                    print("        adapter for the target is missing (no import, not in package.json)")
        print(f"\n{len(results)} swap(s), {failed} incomplete")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
