#!/usr/bin/env python3
"""leak_sweep.py — the release gate for this (public) repo.

Scans for private-project terms before anything is pushed or released:

- the repo working tree (default: this script's repo root),
- every ``*.db`` tracked by git, opened read-only: ``registry='mine'`` rows and
  the TEXT columns of ``registry_items`` / ``templates`` (library_import.py writes the
  owner's free-text ``--source`` into a git-tracked .db, which the text tree walk skips),
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
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

PACK_SKILLS = ["deckhand"]
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", "node_modules", ".next", ".turbo"}
SKIP_EXT = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2",
            ".ttf", ".eot", ".pdf", ".mp3", ".mp4", ".docx", ".xlsx", ".sqlite", ".db",
            ".lock", ".snap"}


def fail(msg) -> NoReturn:
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


def terms_in(text, terms):
    low = text.lower()
    return [t for t in terms if t.lower() in low]


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
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            matches = terms_in(text, terms)
            if matches:
                print(f"HIT  {p}  {matches}")
                hits += len(matches)
    print(f"  {label}: {files} text files scanned, {hits} hit(s)")
    return hits


def sweep_sqlite(path, terms):
    """Gate one SQLite db, opened read-only (``mode=ro`` — nothing is ever written).

    The tree walk skips binaries, but ``library_import.py`` writes the owner's
    free-text ``--source`` into ``registry_items.description`` inside the
    git-tracked ``templates.db`` — so the db gets its own sweep:

    - any ``registry='mine'`` row fails the release (owner-private rows);
    - every TEXT column of ``registry_items`` and ``templates`` is matched with
      the same matcher and message style as the text tree.

    A db without those tables is skipped, not an error. Returns the hit count.
    """
    hits = cells = 0
    path = Path(path)
    if not path.is_file():
        fail(f"tracked db is listed by git but missing from the tree: {path}")
    try:
        con = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    except sqlite3.Error as e:
        fail(f"cannot open tracked db {path} read-only: {e}")
    try:
        tables = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")}
        for table in ("registry_items", "templates"):
            if table not in tables:
                print(f"  tracked db {path}: no {table} table — skipped")
                continue
            info = list(con.execute(f"PRAGMA table_info({table})"))
            if table == "registry_items" and "registry" in [c[1] for c in info]:
                rows = con.execute(
                    "SELECT item FROM registry_items WHERE registry = 'mine'").fetchall()
                if rows:
                    print(f"HIT  {path}  mine rows in tracked db: {len(rows)} row(s) "
                          f"registry='mine' {sorted(r[0] for r in rows)[:10]}")
                    hits += len(rows)
            cols = [c[1] for c in info if (c[2] or "").upper().startswith("TEXT")]
            if not cols:
                continue
            for row in con.execute(f"SELECT rowid, {', '.join(cols)} FROM {table}"):
                cells += len(cols)
                for col, val in zip(cols, row[1:]):
                    if not isinstance(val, str) or not val:
                        continue
                    matches = terms_in(val, terms)
                    if matches:
                        print(f"HIT  {path}  [{table}.{col} rowid={row[0]}]  {matches}")
                        hits += len(matches)
    except sqlite3.Error as e:
        fail(f"tracked db {path} cannot be swept ({e}) — a db the gate cannot read is not a pass")
    finally:
        con.close()
    print(f"  tracked db {path}: {cells} text cell(s) scanned, {hits} hit(s)")
    return hits


def scan_tracked_dbs(repo, terms):
    """Sweep every ``*.db`` in ``git ls-files`` (read-only, see sweep_sqlite)."""
    if not (repo / ".git").exists():
        print("  tracked dbs: no .git here — skipped")
        return 0
    try:
        r = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "--", "*.db"],
                           capture_output=True, text=True, timeout=60)
    except OSError:
        fail("git not found — the tracked-db scan needs it")
        return 0  # unreachable; keeps static analyzers happy
    dbs = [d for d in r.stdout.split("\0") if d.strip()]
    hits = sum(sweep_sqlite(repo / d, terms) for d in dbs)
    print(f"  tracked dbs: {len(dbs)} db(s) swept, {hits} hit(s)")
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
    hits += scan_tracked_dbs(repo, terms)
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
