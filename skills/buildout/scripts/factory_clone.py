#!/usr/bin/env python3
"""factory_clone.py — clone the matched template into a fresh project folder and
write the factory state (.factory/*, PENDING.md). This is the ONLY step that
touches the user's disk, and it runs only on a chosen match.

usage:
  py scripts/factory_clone.py --template Next-Elite --slug my-business [--root D:/] [--install]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _tpl_lib as L  # noqa: E402
import templates_db as DB  # noqa: E402

PENDING_SEED = """# PENDING — only what is mandatory (the owner's real facts)

Everything here is a fact only you can supply. Nothing else blocks go-live.

- [ ] domain name (buy + point DNS)
- [ ] business email that can receive (deliverability: SPF/DKIM on the sending domain)
- [ ] legal identity: legal name, registration/licence number(s), address, tax id
- [ ] real photos (no stock) — logo file + at least 3 real photos or none at all
- [ ] payment method, if the business charges online (provider account or "invoice by hand")
- [ ] go-live target date
"""


def _as_entry_list(swaps) -> list:
    """The registry stores swap_map as {vendor: entry}; the check wants a list."""
    if isinstance(swaps, dict):
        return list(swaps.values())
    return swaps or []


def git(cmd: list[str], cwd: Path, timeout: int = 300) -> tuple[int, str]:
    try:
        p = subprocess.run(["git"] + cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="ignore")
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:  # noqa: BLE001
        return 1, f"{type(e).__name__}: {e}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="clone a matched template into a fresh project folder")
    ap.add_argument("--template", help="name in templates.db")
    ap.add_argument("--repo", help="owner/name (overrides --template's url)")
    ap.add_argument("--slug", required=True, help="project folder name")
    ap.add_argument("--root", default="D:/", help="parent of the project folder (default D:/ — projects live on D:)")
    ap.add_argument("--ref", help="commit/branch (pin it: reproducibility)")
    ap.add_argument("--install", action="store_true", help="run the package manager install after cloning")
    ap.add_argument("--db", default=str(DB.DEFAULT_DB))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    con = DB.connect(Path(args.db))
    row = None
    if args.template:
        r = con.execute("SELECT * FROM templates WHERE name = ?", (args.template,)).fetchone()
        row = DB.rowdict(r) if r else None
        if not row:
            print(f"factory_clone: '{args.template}' not in the registry. Run template_intake.py first.", file=sys.stderr)
            return 2
    repo = args.repo or (row or {}).get("repo")
    if not repo:
        print("factory_clone: no repo (pass --template with a registry row or --repo owner/name)", file=sys.stderr)
        return 2

    if row and not row.get("license_ok"):
        print(f"factory_clone: REFUSED — {repo} has no verified MIT/Apache-2.0 license "
              f"(spdx={row.get('license_spdx')!r}). The pool is permissive-licenses-only.", file=sys.stderr)
        return 4

    dest = Path(args.root) / args.slug
    if dest.exists() and any(dest.iterdir()):
        print(f"factory_clone: {dest} exists and is not empty — refusing to overwrite", file=sys.stderr)
        return 5

    def _as_url(r: str) -> str:
        # local fixture repos are legitimate: a native path (C:/… or ./…) is used as-is.
        # file:// URIs fail in some git builds on Windows — pass a plain path instead.
        if "://" in r or re.match(r"^[A-Za-z]:[/\\]", r) or r.startswith(("/", "./", "../")):
            return r
        return f"https://github.com/{r}"

    url = (row or {}).get("url") or _as_url(repo)
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["clone", "--depth", "1"] + (["--branch", args.ref] if args.ref else []) + [url, str(dest)]
    rc, log = git(cmd, dest.parent)
    if rc != 0:
        print(f"factory_clone: clone failed:\n{log[-500:]}", file=sys.stderr)
        return 6

    commit = ""
    rc, out = git(["rev-parse", "HEAD"], dest)
    if rc == 0:
        commit = out.strip().splitlines()[0]
    shutil.rmtree(dest / ".git", ignore_errors=True)
    rc, _ = git(["init", "-q"], dest)
    git(["checkout", "-q", "-b", "main"], dest)

    state = dest / ".factory"
    state.mkdir(exist_ok=True)
    (state / "match.json").write_text(json.dumps({
        "template": row["name"] if row else repo.split("/")[-1],
        "repo": repo, "url": url, "upstream_commit": commit, "ref": args.ref,
        "license": {"spdx": (row or {}).get("license_spdx"), "file": (row or {}).get("license_file")},
        "stack": (row or {}).get("stack"), "shape": (row or {}).get("shape"),
        "canonical": (row or {}).get("canonical"), "canonical_notes": (row or {}).get("canonical_notes"),
        "cloned_at": DB.now(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (state / "swap-map.json").write_text(json.dumps({
        "project": args.slug, "generated_at": DB.now(), "source": "templates.db",
        "swaps": _as_entry_list((row or {}).get("swap_map")),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (state / "brand.json").write_text(json.dumps({
        "status": "empty — fill during the rebrand phase (ref 40-rebrand.md)",
        "name": None, "tagline": None, "locale_default": None, "locales": None,
        "palette": None, "fonts": None, "logo": None, "voice": None,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (state / "scorecard.md").write_text(
        f"""# Scorecard — {args.slug}

| fact | value |
|---|---|
| template | {row['name'] if row else repo} ({url}) |
| upstream commit | `{commit or '?'}` |
| license | {(row or {}).get('license_spdx') or 'UNVERIFIED'} |
| stack | {json.dumps((row or {}).get('stack') or {}, ensure_ascii=False)} |
| canonical | {(row or {}).get('canonical')} — {(row or {}).get('canonical_notes') or ''} |
| cloned at | {DB.now()} |

Boot evidence is measured, never asserted: install/build/start are recorded in
`templates.db` (boot_*) and re-proved on this clone during the verify phase.
""", encoding="utf-8")
    (dest / "PENDING.md").write_text(PENDING_SEED, encoding="utf-8")

    env_note = ""
    if (dest / ".env.example").exists() and not (dest / ".env").exists():
        shutil.copy(dest / ".env.example", dest / ".env")
        env_note = "env scaffolded from .env.example (fill only what boot needs; real secrets stay out of git)"
        rc_ci, _ = git(["check-ignore", "-q", ".env"], dest)
        if rc_ci != 0:  # the template does not ignore .env -> never let the first commit carry it
            with open(dest / ".gitignore", "a", encoding="utf-8") as gi:
                gi.write("\n# added by buildout factory: never commit secrets\n.env\n")
            env_note += " · .env was not gitignored by the template — added to .gitignore"

    runner = {"pnpm": "pnpm", "npm": "npm", "yarn": "yarn", "bun": "bun"}.get(
        ((row or {}).get("stack") or {}).get("package_manager"), "npm")
    install_ok = None
    if args.install:
        if runner == "pnpm":
            L._run(["pnpm", "config", "set", "store-dir", "D:/pnpm-store"], timeout=60)
        print(f"installing with {runner}...", flush=True)
        rc_i, out_i, err_i = L._run([runner, "install", "--no-audit", "--no-fund"], timeout=1800, cwd=str(dest))
        install_ok = rc_i == 0
        print(f"  install {'ok' if install_ok else 'FAILED'}"
              + ("" if install_ok else f": {(err_i or out_i)[-200:]}"), flush=True)
    git(["add", "-A"], dest)
    rc, out = git(["-c", "user.email=factory@local", "-c", "user.name=buildout-factory",
                   "commit", "-q", "-m", f"chore: clone {row['name'] if row else repo} via buildout factory (upstream {commit[:7]})"], dest)

    result = {"project": str(dest), "template": row["name"] if row else repo, "commit": commit,
              "swap_map_entries": len((row or {}).get("swap_map") or []), "pending": str(dest / "PENDING.md")}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        st = (row or {}).get("stack") or {}
        print(f"cloned {repo} -> {dest}\n  upstream commit {commit[:12]}\n  license {(row or {}).get('license_spdx')}")
        if env_note:
            print(f"  {env_note}")
        print(f"  next: cd {dest} && {runner} install  # then py scripts/swap_check.py --project {dest}")
        print(f"  state: {state}\\  |  mandatory facts: {dest / 'PENDING.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
