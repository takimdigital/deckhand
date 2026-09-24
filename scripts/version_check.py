#!/usr/bin/env python3
"""version_check.py — mechanical release-consistency gate for this pack.

Every human-readable version claim must match machine state. The README version badge is
the location nothing else touches — it has silently lagged the repo (live-hit: the badge
stayed a release behind through tag + release). This script makes that drift impossible to miss.

Checks (stdlib only):
  1. README version badge            ==  pack version in the TOP CHANGELOG.md entry
                                        (the FIRST `## ` heading only — a match in a
                                        later entry is not proof of the top entry)
  2. skills/<name>/SKILL.md version  ==  that skill's CHANGELOG.md top entry (when both exist)
  3. with --tag vX.Y.Z               ==  the release tag being shipped

The test count is deliberately NOT checked here (T14): the hand-retyped number lagged twice,
so the README now carries the CI badge instead (`.github/workflows/ci.yml`) — the suite status
is read from that run, never from a number in a file.

Usage:
  py scripts/version_check.py [--tag vX.Y.Z] [--repo .]
Exit: 0 = VERSIONS OK · 1 = mismatch (each printed) · 2 = usage/IO error
"""
import argparse
import re
import sys
from pathlib import Path


def top_pack_version(changelog: Path):
    """Pack version declared by the FIRST `## ` heading; None if absent/undeclared."""
    for line in changelog.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            m = re.search(r"pack v(\d+\.\d+\.\d+)", line)
            return m.group(1) if m else None
    return None


def top_entry_version(changelog: Path, pattern: str):
    m = re.search(pattern, changelog.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tag", default=None, help="release tag to cross-check, e.g. v0.14.10")
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    ok = True
    rows = []  # (name, got, exp_name, exp, hard) — hard=False renders INFO and never fails the gate

    readme_text = (repo / "README.md").read_text(encoding="utf-8")
    m = re.search(r"version-(\d+\.\d+\.\d+)-blueviolet", readme_text)
    badge = m.group(1) if m else None
    pack = top_pack_version(repo / "CHANGELOG.md")
    rows.append(("README version badge", badge, "pack vX.Y.Z (top CHANGELOG entry)", pack, True))

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
            rows.append((f"skills/{sk.name}", sm.group(1), "own CHANGELOG top entry", "(none — skipped)", False))
            continue
        rows.append((f"skills/{sk.name}", sm.group(1), "own CHANGELOG top entry", ce, True))

    if args.tag:
        rows.append(("release tag", args.tag.lstrip("v"), "README version badge", badge, True))

    for name, got, exp_name, exp, hard in rows:
        matched = got == exp
        if not matched and hard:
            ok = False
        status = "OK " if matched else ("INFO" if not hard else "FAIL")
        print(f"  [{status}] {name}: {got}  vs  {exp_name}: {exp}")

    print("VERSIONS OK" if ok else "VERSIONS FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
