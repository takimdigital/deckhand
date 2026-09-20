#!/usr/bin/env python3
"""library.py - personal component library (add | find | list | show | copy | remove).

Store: $DECKHAND_LIBRARY > $EXPERT_BUILD_LIBRARY (legacy) > ~/deckhand-library
  index.jsonl (query surface) | registry.json | r/<name>.json | items/<name>/ | _archive/

Stdlib only, Python 3.10+.
"""
import argparse, json, os, re, shutil, sys
from datetime import datetime, timezone
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}$")
HEX_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")
IMPORT_RE = re.compile(r"""(?:from\s+['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\s+['"]([^'"]+)['"])""")
SKIP_DEPS = {"react", "react-dom", "next"}

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
        "name": "expert-build-library",
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

def render_item(root, row):
    (root / "r").mkdir(parents=True, exist_ok=True)
    item = {
        "$schema": "https://ui.shadcn.com/schema/registry-item.json",
        "name": row["name"],
        "type": "registry:component",
        "title": row["name"],
        "description": (row.get("source") or "")[:200],
        "dependencies": row.get("deps", []),
        "files": [{"path": f, "type": "registry:component"} for f in row.get("files", [])],
        "categories": row.get("tags", []),
    }
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
    if any(r["name"] == args.name for r in rows) and not args.force:
        print(f"{args.name} already exists (use --force to replace)")
        raise SystemExit(1)
    dest = root / "items" / args.name
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    deps, hexhits, files_rel = set(), [], []
    for f in args.file:
        src = Path(f)
        if not src.exists():
            print(f"file not found: {src}")
            raise SystemExit(1)
        text = src.read_text(encoding="utf-8", errors="ignore")
        deps |= set(extract_deps(text))
        hits = HEX_RE.findall(text)
        if hits:
            hexhits.append(f"{src.name}: {len(hits)} raw hex value(s)")
        shutil.copy2(src, dest / src.name)
        files_rel.append(f"items/{args.name}/{src.name}")
    if hexhits:
        msg = "; ".join(hexhits)
        if args.strict:
            print(f"strict: {msg} - not saved (drop --strict to allow)")
            shutil.rmtree(dest)
            raise SystemExit(1)
        print(f"warning: {msg}")
    row = {
        "name": args.name,
        "tags": sorted({t.strip() for t in (args.tags or "").split(",") if t.strip()}),
        "section": args.section or "",
        "files": files_rel,
        "deps": sorted(deps),
        "source": args.source or "",
        "createdAt": now(),
        "install": f"py scripts/library.py copy {args.name} --to <dir>",
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
        print(f"target dir not found: {target}")
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

def parse_args(argv=None):
    ap = argparse.ArgumentParser(prog="library.py", description="personal component library")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("add")
    a.add_argument("--name", required=True)
    a.add_argument("--file", action="append", required=True)
    a.add_argument("--tags", default="")
    a.add_argument("--section", default="")
    a.add_argument("--source", default="")
    a.add_argument("--strict", action="store_true")
    a.add_argument("--force", action="store_true")
    a.set_defaults(fn=cmd_add)
    f = sub.add_parser("find"); f.add_argument("query"); f.add_argument("--limit", type=int, default=5); f.set_defaults(fn=cmd_find)
    l = sub.add_parser("list"); l.add_argument("--limit", type=int, default=30); l.set_defaults(fn=cmd_list)
    s = sub.add_parser("show"); s.add_argument("name"); s.set_defaults(fn=cmd_show)
    c = sub.add_parser("copy"); c.add_argument("name"); c.add_argument("--to", required=True); c.set_defaults(fn=cmd_copy)
    r = sub.add_parser("remove"); r.add_argument("name"); r.set_defaults(fn=cmd_remove)
    return ap.parse_args(argv)

def main():
    args = parse_args()
    return args.fn(args) or 0

if __name__ == "__main__":
    sys.exit(main())
