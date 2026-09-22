#!/usr/bin/env python3
"""version_check.py — mechanical version-consistency gate for this pack.

The README version badge is the ONE version location that nothing else touches
when a release edits skill files; it has silently lagged a release (live-hit:
it stayed at the previous version through the tag/release). This script makes
that drift impossible to miss.

Checks (offline, stdlib only):
  1. README version badge            ==  pack version in the TOP CHANGELOG.md entry
  2. skills/<name>/SKILL.md version  ==  that skill's CHANGELOG.md top entry (when both exist)
  3. with --tag vX.Y.Z               ==  the release tag being shipped

Usage:
  py scripts/version_check.py [--tag vX.Y.Z] [--repo .]
Exit: 0 = VERSIONS OK · 1 = mismatch (each printed) · 2 = usage/IO error
"""
import argparse
import re
import sys
from pathlib import Path


def top_entry_version(changelog: Path, pattern: str):
    m = re.search(pattern, changelog.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tag", default=None, help="release tag to cross-check, e.g. v0.14.9")
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    ok, rows = True, []

    readme = repo / "README.md"
    m = re.search(r"version-(\d+\.\d+\.\d+)-blueviolet", readme.read_text(encoding="utf-8"))
    badge = m.group(1) if m else None
    pack = top_entry_version(repo / "CHANGELOG.md", r"^## .*pack v(\d+\.\d+\.\d+)")
    rows.append(("README version badge", badge, "pack vX.Y.Z (top CHANGELOG entry)", pack))

    skills_dir = repo / "skills"
    for sk in sorted(skills_dir.iterdir()):
        if not sk.is_dir():
            continue
        sm = re.search(
            r"^version:\s*([0-9][0-9A-Za-z.\-]*)", (sk / "SKILL.md").read_text(encoding="utf-8"), re.M
        )
        if not sm:
            continue
        ch = sk / "CHANGELOG.md"
        ce = top_entry_version(ch, r"^##\s+([0-9][0-9A-Za-z.\-]*)") if ch.exists() else None
        if ce is None:
            rows.append((f"skills/{sk.name}", sm.group(1), "own CHANGELOG top entry", "(none — skipped)"))
            continue
        rows.append((f"skills/{sk.name}", sm.group(1), "own CHANGELOG top entry", ce))

    if args.tag:
        rows.append(("release tag", args.tag.lstrip("v"), "README version badge", badge))

    for name, got, exp_name, exp in rows:
        matched = got == exp
        if not matched and exp != "(none — skipped)":
            ok = False
        print(f"  [{'OK ' if matched else 'FAIL'}] {name}: {got}  vs  {exp_name}: {exp}")

    print("VERSIONS OK" if ok else "VERSIONS FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
