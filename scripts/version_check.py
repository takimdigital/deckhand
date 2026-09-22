#!/usr/bin/env python3
"""version_check.py — mechanical release-consistency gate for this pack.

Every human-readable version/claim must match machine state. The README badges are
the locations nothing else touches — they have silently lagged the repo (live-hit:
the version badge stayed a release behind through tag + release; the tests badge
lagged the suites during a fast release run). This script makes that drift
impossible to miss.

Checks (stdlib only; the suites run under pytest, which this gate REQUIRES):
  1. README version badge            ==  pack version in the TOP CHANGELOG.md entry
                                        (the FIRST `## ` heading only — a match in a
                                        later entry is not proof of the top entry)
  2. README tests badge              ==  pytest total across skills/
  3. README prose "N unit tests"     ==  the same total (the landing page claims it too)
  4. skills/<name>/SKILL.md version  ==  that skill's CHANGELOG.md top entry (when both exist)
  5. with --tag vX.Y.Z               ==  the release tag being shipped

pytest unavailable = FAIL, not skipped (a gate that cannot run is not a gate —
install pytest). --skip-tests is the explicit escape hatch and reports INFO.

Usage:
  py scripts/version_check.py [--tag vX.Y.Z] [--repo .] [--skip-tests]
Exit: 0 = VERSIONS OK · 1 = mismatch (each printed) · 2 = usage/IO error
"""
import argparse
import re
import subprocess
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


def run_suites(repo: Path):
    """Run every skill suite once; return (passed, failed), or None when pytest is unavailable."""
    try:
        p = subprocess.run(
            [sys.executable, "-m", "pytest", "skills", "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    out = (p.stdout or "") + (p.stderr or "")
    if "No module named pytest" in out:
        return None
    passed = failed = None
    for line in reversed(out.splitlines()):
        m = re.search(r"(\d+) passed", line)
        if m and passed is None:
            passed = int(m.group(1))
        m = re.search(r"(\d+) failed", line)
        if m and failed is None:
            failed = int(m.group(1))
        if passed is not None:
            break
    return ((passed or 0), (failed or 0))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tag", default=None, help="release tag to cross-check, e.g. v0.14.10")
    ap.add_argument("--skip-tests", action="store_true", help="skip running the skill suites (INFO only)")
    args = ap.parse_args(argv)
    repo = Path(args.repo)
    ok = True
    rows = []  # (name, got, exp_name, exp, hard) — hard=False renders INFO and never fails the gate

    readme_text = (repo / "README.md").read_text(encoding="utf-8")
    m = re.search(r"version-(\d+\.\d+\.\d+)-blueviolet", readme_text)
    badge = m.group(1) if m else None
    pack = top_pack_version(repo / "CHANGELOG.md")
    rows.append(("README version badge", badge, "pack vX.Y.Z (top CHANGELOG entry)", pack, True))

    if args.skip_tests:
        tb = re.search(r"tests-(\d+)%20passing", readme_text)
        rows.append(("README tests badge", int(tb.group(1)) if tb else None,
                     "skill suites", "(skipped via --skip-tests)", False))
    else:
        tb = re.search(r"tests-(\d+)%20passing", readme_text)
        tests_badge = int(tb.group(1)) if tb else None
        suites = run_suites(repo)
        if suites is None:
            rows.append(("README tests badge", tests_badge, "skill suites",
                         "(pytest unavailable — the gate REQUIRES it; install pytest)", True))
        else:
            passed, failed = suites
            exp = passed if failed == 0 else f"{passed} passed but {failed} FAILING"
            rows.append(("README tests badge", tests_badge, "suites (pytest)", exp, True))
            pm = re.search(r"\*\*(\d+) unit tests\*\*", readme_text)
            rows.append(("README prose tests line", int(pm.group(1)) if pm else None,
                         "suites (pytest)", exp, True))

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
