#!/usr/bin/env python3
"""library.py - personal component library (add | find | list | show | copy | remove).

Store: $DECKHAND_LIBRARY > $EXPERT_BUILD_LIBRARY (legacy) > ~/deckhand-library
  index.jsonl (query surface) | registry.json | r/<name>.json | items/<name>/ | _archive/

Stdlib only, Python 3.10+.

Safety rules (measured, not decorative):
  * a credential-shaped value anywhere in a saved file REFUSES the whole save (never partial);
  * every save records provenance (--source), licence (--license), the licence source URL
    (--source-url) and how the claim was obtained (--license-evidence);
  * r/<name>.json carries each file INLINE (content) so `shadcn add` with a local path installs
    real files (a content-less entry is silently skipped by the CLI), plus a meta block with the
    aliased imports / base / slot the item needs on the other side;
  * re-adding an item whose bytes are identical is a friendly no-op, not an error.
"""
import argparse, hashlib, json, os, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
FONT_RE = re.compile(r"""fontFamily\s*:\s*["'`](?!var\()""")
IMPORT_RE = re.compile(r"""(?:from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\s+['"]([^'"]+)['"])""")
SKIP_DEPS = {"react", "react-dom", "next"}
# Credential shapes (same families the template pipeline refuses). Only shape hints are ever printed.
SECRET_RE = re.compile(
    r"sk_live_[A-Za-z0-9]{10,}|sk_test_[A-Za-z0-9]{10,}|sk-[A-Za-z0-9]{24,}"
    r"|ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY|xox[baprs]-[A-Za-z0-9-]{10,}"
)

def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def store_root():
    for var in ("DECKHAND_LIBRARY", "EXPERT_BUILD_LIBRARY"):
        val = os.environ.get(var)
        if val:
            return Path(val).expanduser()
    legacy = Path.home() / "expert-build-library"
    if legacy.is_dir():
        return legacy  # don't orphan a store made before the rename
    return Path.home() / "deckhand-library"

def extract_deps(text):
    deps = set()
    for m in IMPORT_RE.finditer(text):
        spec = next((g for g in m.groups() if g), None)
        if not spec:
            continue
        if spec.startswith(".") or spec.startswith("/") or spec.startswith("@/"):
            continue
        if spec.startswith("@"):
            deps.add("/".join(spec.split("/")[:2]))
        else:
            deps.add(spec.split("/")[0])
    return sorted(d for d in deps if d not in SKIP_DEPS)

def extract_imports(text):
    """The local/aliased specifiers extract_deps deliberately skips (they bind an item to a project).

    Recorded so a reuse knows what must exist on the other side (a @/components/ui/card import is
    useless without a card). NEVER emitted as registryDependencies: an unknown @scope/name there is
    a hard install error in the shadcn CLI (measured with 4.21.0) - it lives in the item's meta."""
    out = set()
    for m in IMPORT_RE.finditer(text):
        spec = next((g for g in m.groups() if g), None)
        if spec and (spec.startswith(".") or spec.startswith("/") or spec.startswith("@/")):
            out.add(spec)
    return sorted(out)

def secret_hits(text):
    """Shapes only - the matched value is never recorded, only its first 10 chars as a hint."""
    return sorted({m.group(0)[:10] for m in SECRET_RE.finditer(text)})

def read_index(root):
    idx = root / "index.jsonl"
    if not idx.exists():
        return []
    return [json.loads(l) for l in idx.read_text(encoding="utf-8").splitlines() if l.strip()]

def write_index(root, rows):
    (root / "index.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")

def render_registry(root):
    rows = read_index(root)
    reg = {
        "$schema": "https://ui.shadcn.com/schema/registry.json",
        "name": "deckhand-library",
        "homepage": "",
        "items": [
            {
                "name": r["name"],
                "type": "registry:component",
                "title": r["name"],
                "description": (r.get("source") or "")[:200],
                "files": [{"path": f, "type": "registry:component"} for f in r.get("files", [])],
                "dependencies": r.get("deps", []),
                "categories": r.get("tags", []),
            }
            for r in rows
        ],
    }
    (root / "registry.json").write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")

def _inline_files(root, row):
    """files[] with the content inlined - the only shape a LOCAL `shadcn add <path>.json` installs."""
    out = []
    for rel in row.get("files", []):
        entry = {"path": rel, "type": "registry:component"}
        try:
            entry["content"] = (root / rel).read_text(encoding="utf-8")
        except Exception:
            pass  # missing file: verify reports it; no fake content is invented
        out.append(entry)
    return out

def render_item(root, row):
    (root / "r").mkdir(parents=True, exist_ok=True)
    meta = {k: row[k] for k in ("base", "slot", "license", "sourceUrl", "licenseEvidence", "imports") if row.get(k)}
    item = {
        "$schema": "https://ui.shadcn.com/schema/registry-item.json",
        "name": row["name"],
        "type": "registry:component",
        "title": row["name"],
        "description": (row.get("source") or "")[:200],
        "dependencies": row.get("deps", []),
        "files": _inline_files(root, row),
        "categories": row.get("tags", []),
    }
    if meta:
        item["meta"] = meta
    (root / "r" / f"{row['name']}.json").write_text(json.dumps(item, indent=2, ensure_ascii=False), encoding="utf-8")

def search(query, limit=5, root=None):
    root = root or store_root()
    q = (query or "").lower().strip()
    scored = []
    for r in read_index(root):
        s = 0
        name = r["name"].lower()
        tags = [t.lower() for t in r.get("tags", [])]
        if q and name == q:
            s += 10
        elif q and q in name:
            s += 6
        for t in tags:
            if q and t == q:
                s += 8
            elif q and q in t:
                s += 3
        if q and q in (r.get("section") or "").lower():
            s += 4
        if q and q in (r.get("source") or "").lower():
            s += 2
        if s > 0:
            scored.append((s, r))
    scored.sort(key=lambda x: (-x[0], x[1]["name"]))
    return [r for _, r in scored[:limit]]

def cmd_add(args):
    root = store_root()
    if not NAME_RE.match(args.name):
        print(f"invalid name {args.name!r}: lowercase letters, digits, hyphens (2-63 chars)")
        raise SystemExit(1)
    (root / "items").mkdir(parents=True, exist_ok=True)
    rows = read_index(root)
    existing = next((r for r in rows if r["name"] == args.name), None)
    # Validate EVERYTHING before touching the store: nothing is deleted or written until all inputs pass.
    # (Fixed 2026-09-21: --force used to rmtree the old item BEFORE the strict hex check — a rejected
    # re-add left index.jsonl/registry.json advertising files that no longer existed.)
    deps, imports, filehashes = set(), set(), {}
    hexhits, fonthits, secrets, loaded = [], [], [], []
    for f in args.file:
        src = Path(f)
        if src.exists() and src.is_dir():
            print(f"not a file: {src} (pass component files, not directories)")
            raise SystemExit(1)
        if not src.exists():
            print(f"file not found: {src}")
            raise SystemExit(1)
        text = src.read_text(encoding="utf-8", errors="ignore")
        deps |= set(extract_deps(text))
        imports |= set(extract_imports(text))
        filehashes[src.name] = hashlib.sha256(src.read_bytes()).hexdigest()
        if secret_hits(text):
            secrets.append(f"{src.name}: credential-shaped value")
        hits = HEX_RE.findall(text)
        if hits:
            hexhits.append(f"{src.name}: {len(hits)} raw hex value(s)")
        font_hits = FONT_RE.findall(text)
        if font_hits:
            fonthits.append(f"{src.name}: {len(font_hits)} hardcoded font family value(s)")
        loaded.append(src)
    if secrets:
        # Refuse the WHOLE save: nothing partial ever lands in the store.
        print("refusing: " + "; ".join(secrets) + " - credential-shaped values never enter the store")
        raise SystemExit(1)
    if hexhits or fonthits:
        msg = "; ".join(hexhits + fonthits)
        if args.strict:
            print(f"strict: {msg} - not saved (drop --strict to allow)")
            raise SystemExit(1)
        print(f"warning: {msg}")
    if not (args.source or "").strip():
        if args.strict:
            print("strict: no --source - not saved (every stored item names where it came from)")
            raise SystemExit(1)
        print("warning: no --source - the store is untraceable without provenance (set --source)")
    lic = (args.license or "").strip()
    if not lic:
        if args.strict:
            print("strict: no --license - not saved (every stored item records its licence)")
            raise SystemExit(1)
        print("warning: no --license - record it (MIT / Apache-2.0 / ...): a licence that is not "
              "written down cannot be honoured later")
    elif not (args.source_url or "").strip():
        print("warning: --license without --source-url - the claim cannot be re-checked later")
    names = [s.name for s in loaded]
    dups = sorted({n for n in names if names.count(n) > 1})
    if dups:
        print(f"duplicate basenames {dups}: every file of a component needs a unique name - rename and retry")
        raise SystemExit(1)
    if existing and not args.force:
        old = existing.get("fileHashes") or {}
        if old and set(old) == set(filehashes) and all(old[k] == filehashes[k] for k in filehashes):
            print(f"{args.name} is already in your library (saved {existing.get('createdAt', 'earlier')}), nothing changed")
            return 0
        print(f"{args.name} already exists (use --force to replace)")
        raise SystemExit(1)
    dest = root / "items" / args.name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    files_rel = []
    for src in loaded:
        shutil.copy2(src, dest / src.name)
        files_rel.append(f"items/{args.name}/{src.name}")
    row = {
        "name": args.name,
        "tags": sorted({t.strip() for t in (args.tags or "").split(",") if t.strip()}),
        "section": args.section or "",
        "files": files_rel,
        "deps": sorted(deps),
        "imports": sorted(imports),
        "fileHashes": filehashes,
        "license": lic or "unknown",
        "sourceUrl": (args.source_url or "").strip(),
        "licenseEvidence": (args.license_evidence or "").strip(),
        "base": (args.base or "").strip(),
        "slot": (args.slot or "").strip(),
        "depVersions": sorted({v.strip() for v in (args.dep_versions or "").split(",") if v.strip()}),
        "source": args.source or "",
        "createdAt": now(),
        "install": f"py scripts/library.py copy {args.name} --to <dir>   # run from the component-library skill dir",
    }
    rows = [r for r in rows if r["name"] != args.name] + [row]
    rows.sort(key=lambda r: r["name"])
    write_index(root, rows)
    render_registry(root)
    render_item(root, row)
    print(json.dumps(row, ensure_ascii=False))
    return 0

def cmd_find(args):
    hits = search(args.query, limit=args.limit)
    if not hits:
        print("no matches")
        return 1
    for r in hits:
        print(f"{r['name']}  [{','.join(r.get('tags', []))}]  section={r.get('section') or '-'}  files={len(r.get('files', []))}")
    return 0

def cmd_list(args):
    rows = read_index(store_root())
    for r in rows[:args.limit]:
        print(f"{r['name']:<28} [{','.join(r.get('tags', []))}]")
    print(f"({len(rows)} items)")
    return 0

def cmd_show(args):
    row = next((r for r in read_index(store_root()) if r["name"] == args.name), None)
    if not row:
        print(f"{args.name} not found")
        return 1
    print(json.dumps(row, indent=2, ensure_ascii=False))
    return 0

def cmd_copy(args):
    root = store_root()
    row = next((r for r in read_index(root) if r["name"] == args.name), None)
    if not row:
        print(f"{args.name} not found")
        raise SystemExit(1)
    target = Path(args.to)
    if not target.exists():
        target.mkdir(parents=True)
        print(f"created target dir: {target}")
    missing = [rel for rel in row.get("files", []) if not (root / rel).exists()]
    if missing:
        print(f"store is inconsistent: missing {', '.join(missing)} - the item dir was altered; re-add or remove it")
        raise SystemExit(1)
    if target.exists() and not target.is_dir():
        print(f"--to must be a directory: {target}")
        raise SystemExit(1)
    clobber = [rel for rel in row.get("files", []) if (target / Path(rel).name).exists()]
    if clobber and not getattr(args, "force", False):
        print(f"refusing to overwrite {len(clobber)} existing file(s) in {target}: "
              f"{', '.join(sorted(Path(r).name for r in clobber))} - pass --force to replace")
        raise SystemExit(1)
    for rel in row.get("files", []):
        src = root / rel
        shutil.copy2(src, target / Path(rel).name)
        print(str(target / Path(rel).name))
    return 0

def cmd_remove(args):
    root = store_root()
    rows = read_index(root)
    row = next((r for r in rows if r["name"] == args.name), None)
    if not row:
        print(f"{args.name} not found")
        return 1
    archive = root / "_archive" / f"{args.name}-{now().replace(':', '')}"
    archive.parent.mkdir(parents=True, exist_ok=True)
    src = root / "items" / args.name
    if src.exists():
        shutil.move(str(src), str(archive))
    rfile = root / "r" / f"{args.name}.json"
    if rfile.exists():
        rfile.unlink()
    write_index(root, [r for r in rows if r["name"] != args.name])
    render_registry(root)
    print(f"archived -> {archive}")
    return 0

def cmd_verify(args):
    root = store_root()
    rows = read_index(root)
    items = sorted(p.name for p in (root / "items").iterdir() if p.is_dir()) if (root / "items").is_dir() else []
    problems = []
    if len(rows) != len(items):
        problems.append(f"index has {len(rows)} rows, items/ has {len(items)} dirs")
    for r in rows:
        if r["name"] not in items:
            problems.append(f"row {r['name']} has no items/ dir")
        for rel in r.get("files", []):
            if not (root / rel).exists():
                problems.append(f"{r['name']}: missing {rel}")
        for base, h in (r.get("fileHashes") or {}).items():
            f = root / "items" / r["name"] / base
            if f.exists() and hashlib.sha256(f.read_bytes()).hexdigest() != h:
                problems.append(f"{r['name']}: {base} changed since it was saved (hash mismatch)")
    if problems:
        print("VERIFY FAILED")
        for p in problems:
            print(" -", p)
        return 1
    print(f"VERIFY OK - {len(rows)} items; index, dirs, files and hashes agree")
    return 0

def cmd_where(args):
    print(store_root())
    return 0

def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="library.py", description="personal component library")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--name", required=True)
    a.add_argument("--file", action="append", required=True)
    a.add_argument("--tags", default="")
    a.add_argument("--section", default="")
    a.add_argument("--source", default="")
    a.add_argument("--license", default="")
    a.add_argument("--source-url", default="")
    a.add_argument("--license-evidence", default="")
    a.add_argument("--base", default="", choices=["", "radix", "base-ui", "aria", "none"])
    a.add_argument("--slot", default="")
    a.add_argument("--dep-versions", default="")
    a.add_argument("--strict", action="store_true")
    a.add_argument("--force", action="store_true")
    a.set_defaults(fn=cmd_add)
    f = sub.add_parser("find"); f.add_argument("query"); f.add_argument("--limit", type=int, default=5); f.set_defaults(fn=cmd_find)
    l = sub.add_parser("list"); l.add_argument("--limit", type=int, default=30); l.set_defaults(fn=cmd_list)
    s = sub.add_parser("show"); s.add_argument("name"); s.set_defaults(fn=cmd_show)
    c = sub.add_parser("copy"); c.add_argument("name"); c.add_argument("--to", required=True); c.add_argument("--force", action="store_true"); c.set_defaults(fn=cmd_copy)
    v = sub.add_parser("verify"); v.set_defaults(fn=cmd_verify)
    w = sub.add_parser("where"); w.set_defaults(fn=cmd_where)
    r = sub.add_parser("remove"); r.add_argument("name"); r.set_defaults(fn=cmd_remove)
    return ap.parse_args(argv)

def main():
    args = parse_args()
    return args.fn(args) or 0

if __name__ == "__main__":
    sys.exit(main())
