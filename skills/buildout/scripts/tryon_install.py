#!/usr/bin/env python3
"""tryon_install — put the try-on plumbing into a project (dev-only, journaled, reversible).

    py scripts/tryon_install.py install   --project D:/app [--port 7799] [--force]
    py scripts/tryon_install.py uninstall --project D:/app [--force-leave-swaps]
    py scripts/tryon_install.py status    --project D:/app

What install does (never touches components/ui, never edits anything else):
  1. writes .tryon/loader.cjs       (dev-only source-mapping loader, NODE_ENV-gated at config time)
  2. writes components/dev/tryon-dev.tsx (mounts the overlay script in development only)
  3. patches next.config.<ext>       (registers the loader; refused -> exit 4 + snippet to paste)
  4. patches app/layout.tsx          (imports + renders TryOnDev before </body>)

Every patched file is backed up byte-for-byte in .tryon/backups/ and recorded in .tryon/journal.json;
`uninstall` restores the patches byte-exact and deletes only the files this tool created. It refuses
(exit 5, nothing touched) while swap.mjs still has live swap rows in that shared journal — they are
the only record of the owner's original imports; revert them first, or pass --force-leave-swaps to
take the plumbing out and keep them. Either way it reports (`staged_left`) the staged variants no
remaining swap points at — never deletes them, the owner's code may import them.
Exit codes: 0 ok · 2 usage · 4 manual step needed · 5 not a supported project (or a live swap
refusing an uninstall).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
TPL = SKILL / "templates" / "tryon"

START = "// tryon:start"
END = "// tryon:end"


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def read_raw(p: Path) -> str:
    """Read exactly these bytes as UTF-8 — never let the OS translate newlines (LF must stay LF)."""
    return p.read_bytes().decode("utf-8")


def write_raw(p: Path, text: str) -> None:
    """Write exactly these bytes — no newline translation, so uninstall can be byte-exact."""
    p.write_bytes(text.encode("utf-8"))


def load_journal(project: Path) -> list[dict]:
    p = project / ".tryon" / "journal.json"
    if p.exists():
        try:
            return json.loads(read_raw(p))
        except Exception:
            return []
    return []


def save_journal(project: Path, j: list[dict]) -> None:
    write_raw(project / ".tryon" / "journal.json", json.dumps(j, indent=1))


def backup(project: Path, rel: str, text: str) -> str:
    b = project / ".tryon" / "backups" / (rel.replace("/", "__") + ".bak")
    b.parent.mkdir(parents=True, exist_ok=True)
    write_raw(b, text)
    return str(b.relative_to(project)).replace("\\", "/")


def find_config(project: Path) -> Path | None:
    for name in ("next.config.ts", "next.config.mjs", "next.config.js", "next.config.cjs"):
        p = project / name
        if p.exists():
            return p
    return None


def _paths(project: Path) -> tuple[str, str]:
    return (project / ".tryon" / "loader.cjs").as_posix(), project.as_posix()


def _loaders(project: Path) -> str:
    loader, root = _paths(project)
    return f'{{ loaders: [{{ loader: "{loader}", options: {{ root: "{root}" }} }}] }}'


def next_version(project: Path) -> tuple[int, int] | None:
    """The project's Next version, from its own install.

    It decides WHERE our rule lives, and guessing wrong means a silently ignored rule:
      * >= 15.3 (and 16.x): the stable top-level `turbopack.rules`
      * < 15.3: `experimental.turbo.rules`
    Measured on 15.6.0-canary.59: `experimental.turbo` → "Unrecognized key(s) in object: 'turbo'",
    and `rules` missing from `turbopack` → "Unrecognized key(s) in object: '**/*.{jsx,tsx}'"."""
    try:
        v = json.loads(read_raw(project / "node_modules" / "next" / "package.json")).get("version", "")
        m = re.match(r"(\d+)\.(\d+)", v)
        return (int(m.group(1)), int(m.group(2))) if m else None
    except Exception:
        return None


def old_school(project: Path) -> bool:
    """Next < 15.3 only understands `experimental.turbo.rules` (the pre-stable-key location)."""
    v = next_version(project)
    return v is not None and (v[0] < 15 or (v[0] == 15 and v[1] < 3))


def loader_binding(project: Path, port: int) -> str:
    """The whole `turbopack` key (Next 16+), for a config that defines none.

    Gated at CONFIG time on NODE_ENV via a spread — `condition` inside a Turbopack rule is a
    matcher, NOT an env gate (measured: a static rule stamped 4 files into a production .next)."""
    return (f'{START} (dev-only source mapping; remove with scripts/tryon_install.py uninstall)\n'
            f'  ...(process.env.NODE_ENV === "development" ? {{ turbopack: {{ rules: {{ "**/*.{{jsx,tsx}}": '
            f'{_loaders(project)} }} }} }} : {{}}),\n'
            f'  {END}')


def turbo_binding(project: Path, port: int) -> str:
    """The whole `experimental.turbo` key (Next 15), for a config that defines no `experimental`."""
    return (f'{START} (dev-only source mapping; remove with scripts/tryon_install.py uninstall)\n'
            f'  ...(process.env.NODE_ENV === "development" ? {{ experimental: {{ turbo: {{ rules: '
            f'{{ "**/*.{{jsx,tsx}}": {_loaders(project)} }} }} }} }} : {{}}),\n'
            f'  {END}')


def rules_binding(project: Path) -> str:
    """The complete `rules: { … }` entry, for a config whose `turbopack` object exists but carries no
    rules yet. The spread is gated on NODE_ENV so it stays dev-only even inside someone else's key."""
    return (f'{START} (dev-only source mapping; remove with scripts/tryon_install.py uninstall)\n'
            f'    rules: {{\n'
            f'      ...(process.env.NODE_ENV === "development" ? {{ "**/*.{{jsx,tsx}}": '
            f'{_loaders(project)} }} : {{}}),\n'
            f'    }},\n'
            f'  {END}')


def turbo_rules_binding(project: Path) -> str:
    """`turbo: { rules: { … } }`, for a Next 15 config that already owns `experimental: {...}`."""
    return (f'{START} (dev-only source mapping; remove with scripts/tryon_install.py uninstall)\n'
            f'    turbo: {{ rules: {{ ...(process.env.NODE_ENV === "development" ? {{ "**/*.{{jsx,tsx}}": '
            f'{_loaders(project)} }} : {{}}) }} }},\n'
            f'  {END}')


def _object_span(text: str, key: str) -> tuple[int, str] | None:
    """(index just after `key: {`, its body) for an object-literal value; None when absent."""
    m = re.search(rf"\b{key}\s*:\s*\{{", text)
    if not m:
        return None
    tail = text[m.end():]
    depth, end = 1, len(tail)
    for i, ch in enumerate(tail):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    return m.end(), tail[:end]


def patch_config(project: Path, port: int) -> tuple[str, str]:
    cfg = find_config(project)
    if cfg is None:
        return "missing", "no next.config.* found"
    text = read_raw(cfg)
    rel = cfg.relative_to(project).as_posix()
    if START in text:
        return "already", rel
    legacy = old_school(project)

    def commit(new: str) -> tuple[str, str]:
        b = backup(project, rel, text)
        write_raw(cfg, new)
        j = load_journal(project)
        j.append({"kind": "patch", "file": rel, "backup": b, "shaBefore": sha(text), "shaAfter": sha(new)})
        save_journal(project, j)
        return "patched", rel

    def merge_into(key: str, inner_key: str | None, binding: str) -> tuple[str, str] | None:
        """Insert our spread into the owner's `key: {...}` object; refuse when a same-purpose child
        object is already there (a second transform on the same files beats a silent double run)."""
        span = _object_span(text, key)
        if not span:
            return None
        at, body = span
        if inner_key and re.search(rf"\b{inner_key}\s*:", body):
            return "manual", (f"{rel} already defines `{key}.{inner_key}`; add this by hand:\n  {binding}")
        if not inner_key and re.search(r"\brules\s*:", body):
            return "manual", (f"{rel} already defines `{key}.rules`; add this by hand:\n  {binding}")
        return commit(text[:at] + "\n  " + binding + text[at:])

    if legacy:
        got = merge_into("experimental", "turbo", turbo_rules_binding(project))
        if got:
            return got
        if re.search(r"\bexperimental\b", text):
            return "manual", (f"{rel} mentions `experimental` but not as an object literal; merge by hand:\n"
                              f"  {turbo_binding(project, port)}")
        pending = turbo_binding(project, port)
    else:
        got = merge_into("turbopack", None, rules_binding(project))
        if got:
            return got
        if re.search(r"\bturbopack\b", text):
            return "manual", (f"{rel} mentions `turbopack` but not as an object literal; merge by hand:\n"
                              f"  {loader_binding(project, port)}")
        pending = loader_binding(project, port)

    m = re.search(r"export\s+default\s*\{|module\.exports\s*=\s*\{", text)
    if not m:
        # `export default nextConfig;` and the plugin-wrapped shape `export default withX(nextConfig);`
        ed = re.search(r"export\s+default\s+(?:[\w$.]+\s*\(\s*)*([A-Za-z_$][\w$]*)", text)
        if ed:
            var = re.search(r"(?:const|let|var)\s+" + re.escape(ed.group(1)) + r"\s*(?::[^=]+)?=\s*\{", text)
            if var:
                m = var
    if not m:
        return "manual", (f"{rel}: config shape not recognised; add this inside your config object:\n"
                          f"  {pending}")
    return commit(text[:m.end()] + "\n  " + pending + text[m.end():])


def src_dir(project: Path) -> str:
    """'' when the app sits at the root, 'src' when it uses a src directory (alias @/* -> ./src/*)."""
    if (project / "src" / "app").exists():
        return "src"
    try:
        ts = read_raw(project / "tsconfig.json")
        if re.search(r'"@/\*"\s*:\s*\[\s*"\./src/', ts):
            return "src"
    except Exception:
        pass
    return ""


def find_layout(project: Path) -> Path | None:
    """Root layout first; then the next-intl shape (src/app/[locale]/layout.tsx); then any layout."""
    for rel in ("app/layout.tsx", "src/app/layout.tsx", "src/app/[locale]/layout.tsx", "app/[locale]/layout.tsx"):
        p = project / rel
        if p.exists():
            return p
    for pat in ("src/app/**/layout.tsx", "app/**/layout.tsx"):
        hits = sorted(project.glob(pat), key=lambda p: (len(p.parts), str(p)))
        if hits:
            return hits[0]
    return None


def patch_layout(project: Path) -> tuple[str, str]:
    lay = find_layout(project)
    if lay is None:
        return "missing", "no app/layout.tsx (or src/app/**/layout.tsx) found — App Router required for v1"
    text = read_raw(lay)
    rel = lay.relative_to(project).as_posix()
    if "TryOnDev" in text:
        return "already", rel
    if "</body>" not in text:
        return "manual", f"{rel}: no </body> to anchor on"
    import_line = 'import TryOnDev from "@/components/dev/tryon-dev";\n'
    m = re.search(r"^(import .*?;)\s*$", text, re.M)
    if m:
        # insert after the LAST top-level import line
        last = None
        for mm in re.finditer(r"^import .*?;\s*$", text, re.M):
            last = mm
        assert last is not None
        text2 = text[: last.end()] + "\n" + import_line + text[last.end():]
    else:
        text2 = import_line + text
    # JSX comment, not `//`: a `//` marker inside JSX renders as literal page text (measured).
    # The usage is folded at build time, so a production page never references the dev mount.
    marker = (f"{{/* tryon:start dev-only overlay mount */}}\n"
              f"      {{process.env.NODE_ENV === \"development\" ? <TryOnDev /> : null}}\n"
              f"      {{/* tryon:end */}}")
    text3 = text2.replace("</body>", f"  {marker}\n    </body>", 1)
    b = backup(project, rel, text)
    write_raw(lay, text3)
    j = load_journal(project)
    j.append({"kind": "patch", "file": rel, "backup": b, "shaBefore": sha(text), "shaAfter": sha(text3)})
    save_journal(project, j)
    return "patched", rel


def ensure_gitignore(project: Path, dev_rel: str) -> tuple[str, str]:
    """Keep the token and the dev mount out of git: `.tryon/` and the dev component dir.

    A single `git add -A` must never be able to publish `.tryon/server.json` (it holds the live
    token) — measured: neither path was ignored in any installed project. Rules are appended
    idempotently; the edit is journaled like any other patch so uninstall stays byte-exact."""
    dev_dir = dev_rel.rsplit("/", 1)[0] if "/" in dev_rel else dev_rel
    rules = [".tryon/", dev_dir + "/"]
    p = project / ".gitignore"
    if p.exists():
        text = read_raw(p)
        have = {ln.strip() for ln in text.splitlines()}
        missing = [r for r in rules if r not in have]
        if not missing:
            return "already", ".gitignore"
        new = text if (text == "" or text.endswith("\n")) else text + "\n"
        new += "\n# try-on (dev-only; .tryon/server.json holds the local token)\n" + "\n".join(missing) + "\n"
        b = backup(project, ".gitignore", text)
        write_raw(p, new)
        j = load_journal(project)
        j.append({"kind": "patch", "file": ".gitignore", "backup": b, "shaBefore": sha(text), "shaAfter": sha(new)})
        save_journal(project, j)
        return "patched", ".gitignore"
    text = "# created by try-on install (dev-only; .tryon/server.json holds the local token)\n" + "\n".join(rules) + "\n"
    write_raw(p, text)
    j = load_journal(project)
    j.append({"kind": "create", "file": ".gitignore", "shaAfter": sha(text)})
    save_journal(project, j)
    return "created", ".gitignore"


def cmd_install(args) -> int:
    project = Path(args.project).resolve()
    if not (project / "package.json").exists():
        print(json.dumps({"ok": False, "reason": "no package.json", "project": str(project)}))
        return 5
    if find_config(project) is None:
        print(json.dumps({"ok": False, "reason": "not a Next.js project (no next.config.*); "
                          "v1 supports Next apps — see references/tryon.md for other stacks"}))
        return 5
    st = project / ".tryon"
    st.mkdir(exist_ok=True)
    (st / "backups").mkdir(exist_ok=True)
    created, outcomes = [], []

    # 1. loader (always refresh from the skill: it is OUR file, not the owner's)
    dest = st / "loader.cjs"
    shutil.copyfile(TPL / "loader.cjs", dest)
    created.append(".tryon/loader.cjs")

    # 2. token/port
    cfgp = st / "server.json"
    try:
        cfg = json.loads(read_raw(cfgp))
    except Exception:
        cfg = {}
    import secrets
    cfg.setdefault("port", args.port or 7799)
    cfg.setdefault("token", secrets.token_hex(12))
    write_raw(cfgp, json.dumps(cfg, indent=1))

    # 3. dev mount component (token+port baked in so the page needs no arguments)
    sd = src_dir(project)
    rel_name = f"{sd}/components/dev/tryon-dev.tsx" if sd else "components/dev/tryon-dev.tsx"
    dev = project / rel_name
    dev.parent.mkdir(parents=True, exist_ok=True)
    tsx = read_raw(TPL / "tryon-dev.tsx")
    tsx = tsx.replace("__TRYON_PORT__", str(cfg["port"])).replace("__TRYON_TOKEN__", cfg["token"])
    write_raw(dev, tsx)
    created.append(rel_name)

    # 4. patches (journaled, byte-backed-up)
    outcomes.append(("config",) + patch_config(project, cfg["port"]))
    outcomes.append(("layout",) + patch_layout(project))
    outcomes.append(("gitignore",) + ensure_gitignore(project, rel_name))

    manual = [o for o in outcomes if o[1] == "manual"]
    out = {
        "ok": not manual,
        "project": str(project),
        "created": created,
        "config": {"state": outcomes[0][1], "detail": outcomes[0][2]},
        "layout": {"state": outcomes[1][1], "detail": outcomes[1][2]},
        "gitignore": {"state": outcomes[2][1], "detail": outcomes[2][2]},
        "port": cfg["port"],
        "next": [
            f"1. start the helper:  py {SKILL.as_posix()}/scripts/tryon_server.py serve --project {project.as_posix()}",
            f"2. start the app:     (in {project.name}) npm run dev  (or pnpm dev)",
            f"3. open the site and click Try-On in the corner; overlay: http://127.0.0.1:{cfg['port']}/overlay.js",
            f"4. agent loop:        py {SKILL.as_posix()}/scripts/tryon_server.py wait --project {project.as_posix()}",
        ],
        "revert": f"py {SKILL.as_posix()}/scripts/tryon_install.py uninstall --project {project.as_posix()}",
    }
    print(json.dumps(out, indent=1))
    return 0 if not manual else 4


def _variant_key(rel: str) -> str:
    """A staged-variant reference, normalised for comparison and alias/extension agnostic:
    `@/components/variants/button/x.tsx` and `components/variants/button/x` → the same string."""
    p = str(rel).replace("\\", "/").strip()
    p = re.sub(r"^[@~]/", "", p)
    p = re.sub(r"^\.?/+", "", p)
    return re.sub(r"\.(tsx|ts|jsx|js|mjs)$", "", p)


def staged_variants_left(project: Path, live: list[dict]) -> list[str]:
    """Staged variants no live swap points at any more.

    Owner work may import them (a Keep, a copy, a hand-tweak), so they are reported, never deleted."""
    try:
        man = json.loads(read_raw(project / ".tryon" / "manifest.json"))
    except Exception:
        return []
    wired = {_variant_key(e.get("to", "")) for e in live}
    out = []
    for m in man if isinstance(man, list) else []:
        dest = str((m or {}).get("dest") or "").replace("\\", "/")
        if "components/variants/" not in dest or not (project / dest).exists():
            continue
        if _variant_key(dest) not in wired:
            out.append(dest)
    return sorted(set(out))


def cmd_uninstall(args) -> int:
    project = Path(args.project).resolve()
    j = load_journal(project)
    swaps = [e for e in j if e.get("kind") is None and "local" in e]
    if swaps and not getattr(args, "force_leave_swaps", False):
        # The swap rows (swap.mjs: `local`/`from`/`to`, no `kind`) are the ONLY record of the owner's
        # own imports; uninstall is the 'put it back' verb, so it must refuse rather than drop them.
        print(json.dumps({
            "ok": False,
            "reason": "SWAPS_ACTIVE",
            "files": sorted({e["file"] for e in swaps}),
            "hint": f"node {(TPL / 'swap.mjs').as_posix()} revert --all --root {project.as_posix()}"
                    "  (or keep them first)",
        }))
        return 5
    restored, kept, removed = [], [], []
    for entry in reversed(j):
        f = project / entry["file"]
        if entry.get("kind") == "create":
            # a file WE created (e.g. .gitignore on a project that had none): delete only if untouched
            if f.exists() and sha(read_raw(f)) == entry.get("shaAfter"):
                f.unlink()
                removed.append(entry["file"])
            continue
        if entry.get("kind") != "patch" or "backup" not in entry:
            continue  # swap rows are not ours to revert here
        b = project / entry["backup"]
        if not b.exists():
            continue
        cur = read_raw(f) if f.exists() else ""
        if sha(cur) == entry.get("shaAfter"):
            write_raw(f, read_raw(b))
            restored.append(entry["file"])
        else:
            kept.append(entry["file"])  # owner edited it since — never overwrite real work
    for rel in (".tryon/loader.cjs", "components/dev/tryon-dev.tsx", "src/components/dev/tryon-dev.tsx"):
        f = project / rel
        if f.exists():
            f.unlink()
            removed.append(rel)
    for devdir in (project / "components" / "dev", project / "src" / "components" / "dev"):
        if devdir.exists() and not any(devdir.iterdir()):
            devdir.rmdir()
    remaining = [e for e in j if e.get("file") in kept or e in swaps]
    save_journal(project, remaining)
    out = {"ok": True, "restored": restored, "removed": removed, "kept_modified_by_owner": kept,
           "staged_left": staged_variants_left(
               project, [e for e in remaining if e.get("kind") is None and "local" in e]),
           "note": "files you edited since install are never reverted silently"}
    print(json.dumps(out, indent=1))
    return 0


def cmd_status(args) -> int:
    project = Path(args.project).resolve()
    j = load_journal(project)
    out = {"project": str(project), "installed": (project / ".tryon" / "loader.cjs").exists(),
           "server": None, "journal": j}
    cfg = project / ".tryon" / "server.json"
    if cfg.exists():
        out["server"] = json.loads(read_raw(cfg))
    print(json.dumps(out, indent=1))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="try-on installer (dev-only, journaled)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("install")
    p.add_argument("--project", required=True)
    p.add_argument("--port", type=int, default=0)
    p.add_argument("--force", action="store_true")
    p = sub.add_parser("uninstall")
    p.add_argument("--project", required=True)
    p.add_argument("--force-leave-swaps", action="store_true",
                   help="uninstall the plumbing but keep live swaps journaled (revert later with swap.mjs revert)")
    p = sub.add_parser("status")
    p.add_argument("--project", required=True)
    args = ap.parse_args(argv)
    return {"install": cmd_install, "uninstall": cmd_uninstall, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
