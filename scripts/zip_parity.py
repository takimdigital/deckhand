#!/usr/bin/env python3
"""zip_parity.py — byte-level parity check: every zip entry must equal the repo file.

Entry-COUNT parity is not enough: stale content slips through (a zip can carry the
right file names at old versions — it happened). This compares bytes for every entry
and fails loudly on any difference, missing name, or extra name.

Usage:
  py scripts/zip_parity.py <zip> [repo-root=.]

Exit: 0 = PARITY OK · 1 = differences (each printed) · 2 = usage/IO error
"""
import os
import sys
import zipfile
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".next", "node_modules"}


def main(argv):
    if not argv:
        print((__doc__ or "").strip())
        return 2
    zpath = Path(argv[0])
    repo = Path(argv[1]) if len(argv) > 1 else Path(".")
    if not zpath.exists():
        print(f"zip not found: {zpath}")
        return 2
    z = zipfile.ZipFile(zpath)
    names = sorted(n for n in z.namelist() if not n.endswith("/"))

    diffs, missing = [], []
    for n in names:
        rp = repo / n
        if not rp.exists():
            missing.append(n)
            continue
        if z.read(n) != rp.read_bytes():
            diffs.append(n)

    tracked = set()
    for root, dirs, files in os.walk(repo):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            tracked.add((Path(root) / f).relative_to(repo).as_posix())
    extra = sorted(t for t in tracked if t not in set(names))

    print(
        f"entries: {len(names)} | byte-diffs: {len(diffs)} | "
        f"missing-in-repo: {len(missing)} | repo-files-not-in-zip: {len(extra)}"
    )
    for label, rows in (("BYTE-DIFF", diffs), ("MISSING-IN-REPO", missing), ("NOT-IN-ZIP", extra)):
        for r in rows:
            print(f"  {label}: {r}")

    ok = not (diffs or missing or extra)
    print("PARITY OK" if ok else "PARITY FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
