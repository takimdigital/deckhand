#!/usr/bin/env python3
"""leak_sweep.py — the release gate for this (public) repo.

Scans for private-project terms before anything is pushed or released:

- the repo working tree (default: this script's repo root),
- the commit messages of the repo's branches and tags,
- every harness copy of the pack skills (hermes install + the .claude/.agents/.codex mirrors),
- any extra files passed with --file (a release-notes draft — that is the exact moment
  wordings leak in) and directories passed with --dir.

Terms come from a private, never-published list: ``~/.deckhand/private-terms.txt``
(one per line, '#' comments allowed). If the list is missing, the gate FAILS (exit 2)
rather than passing silently — a gate that cannot check is not a gate.

Usage:
  py scripts/leak_sweep.py [--repo DIR] [--terms FILE] [--file NOTES.md]... [--dir DIR]...

Exit: 0 clean · 1 hits · 2 setup problem (missing terms list, bad path).
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

PACK_SKILLS = ["buildout", "component-library", "vps-ops", "session-autopsy", "deckhand-profile"]
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".next", ".turbo"}
SKIP_EXT = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2",
            ".ttf", ".eot", ".pdf", ".mp3", ".mp4", ".docx", ".xlsx", ".sqlite", ".db",
            ".lock", ".snap"}


def fail(msg):
    print(f"leak_sweep: {msg}", file=sys.stderr)
    sys.exit(2)


def load_terms(path):
    p = Path(path).expanduser()
    if not p.is_file():
        fail(f"terms list not found at {p} — create it (one private term per line) or pass --terms; "
             "refusing to pass silently")
    terms = [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    if not terms:
        fail(f"terms list at {p} is empty — checking nothing is not a pass")
    return terms


def is_text(path):
    if path.suffix.lower() in SKIP_EXT:
        return False
    try:
        with path.open("rb") as f:
            return b"\x00" not in f.read(8192)
    except OSError:
        return False


def scan_tree(root, terms, label):
    files = hits = 0
    root = Path(root)
    if not root.is_dir():
        fail(f"scan target is not a directory: {root}")
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if not is_text(p):
                continue
            files += 1
            try:
                low = p.read_text(encoding="utf-8", errors="replace").lower()
            except OSError:
                continue
            matches = [t for t in terms if t.lower() in low]
            if matches:
                print(f"HIT  {p}  {matches}")
                hits += len(matches)
    print(f"  {label}: {files} text files scanned, {hits} hit(s)")
    return hits


def scan_history(repo, terms):
    hits = 0
    if not (repo / ".git").exists():
        print("  history: no .git here — skipped")
        return 0
    for term in terms:
        try:
            r = subprocess.run(
                ["git", "-C", str(repo), "log", "--branches", "--tags", "-i",
                 "--grep", term, "--format=%h %s"],
                capture_output=True, text=True, timeout=60)
        except OSError:
            fail("git not found — the history scan needs it")
            return hits  # unreachable; keeps static analyzers happy
        for line in r.stdout.splitlines():
            if line.strip():
                print(f"HIT  commit {line}  <-- {term!r}")
                hits += 1
    print(f"  history: {hits} hit(s)")
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(prog="leak_sweep.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]),
                    help="repo root to scan (default: this script's repo)")
    ap.add_argument("--terms", default=str(Path.home() / ".deckhand" / "private-terms.txt"),
                    help="the private terms list (never stored in the repo)")
    ap.add_argument("--file", action="append", default=[], help="extra file (e.g. a notes draft)")
    ap.add_argument("--dir", action="append", default=[], help="extra directory to scan")
    a = ap.parse_args(argv)

    terms = load_terms(a.terms)
    repo = Path(a.repo).expanduser().resolve()
    print(f"leak_sweep: {len(terms)} term(s); repo={repo}")
    hits = scan_tree(repo, terms, "repo tree")
    hits += scan_history(repo, terms)

    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA", str(home / "AppData" / "Local")))
    bases = [home / ".claude" / "skills", home / ".agents" / "skills", home / ".codex" / "skills",
             local / "hermes" / "skills" / "software-development"]
    checked = f_hits = 0
    for base in bases:
        for s in PACK_SKILLS:
            d = base / s
            if d.is_dir():
                checked += 1
                f_hits += scan_tree(d, terms, f"copy {d}")
    print(f"  harness copies: {checked} dirs checked, {f_hits} hit(s)")
    hits += f_hits

    for f in a.file:
        p = Path(f).expanduser()
        if not p.is_file():
            fail(f"--file not found: {p}")
        low = p.read_text(encoding="utf-8", errors="replace").lower()
        matches = [t for t in terms if t.lower() in low]
        if matches:
            print(f"HIT  {p}  {matches}")
            hits += len(matches)
        else:
            print(f"  file OK: {p}")

    for d in a.dir:
        hits += scan_tree(Path(d).expanduser(), terms, f"extra dir {d}")

    if hits:
        print(f"\nleak_sweep: {hits} HIT(S) — fix these before any push or release")
        return 1
    print("\nleak_sweep: CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
