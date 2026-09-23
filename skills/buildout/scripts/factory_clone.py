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
import os
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


def _scan_clone_for_vendors(dest: Path) -> dict:
    """Vendors visible in the CLONE: package.json deps + README/.env.example/Dockerfile text.

    The registry row only knows what intake measured from dep names; a vendor that appears only in
    code, env examples or the Dockerfile would otherwise never reach the swap map.
    """
    deps: list[str] = []
    pkg_path = dest / "package.json"
    if pkg_path.exists():
        try:
            pkg = json.loads(pkg_path.read_text(encoding="utf-8", errors="ignore"))
            deps = list((pkg.get("dependencies") or {}).keys()) + list((pkg.get("devDependencies") or {}).keys())
        except Exception:  # noqa: BLE001
            deps = []
    blob = ""
    for name in ("README.md", ".env.example", "Dockerfile", "docker-compose.yml", "compose.yaml"):
        p = dest / name
        if p.exists():
            blob += p.read_text(encoding="utf-8", errors="ignore")[:20000] + "\n"
    _v, _s, _u, swap_map, _m = L.classify_deps(deps, blob)
    return swap_map


def _merge_swaps(reg: list, local: dict) -> list:
    """Registry entries win; vendors found only by the local scan are added, marked with source.

    `target_patterns`/`removal_ok` are DERIVED facts, so they are refreshed from the current vendor
    table even on registry entries — a map stored by an older intake must not keep prose targets
    ("socket.io-or-sse") that the gate can never match. Human fields (status, allow, note) survive.
    """
    out: dict = {}
    for e in reg:
        if isinstance(e, dict) and e.get("vendor"):
            e = dict(e)
            e.setdefault("source", "templates.db")
            fresh = L.TARGET_PATTERNS.get(e.get("target") or "")
            if fresh:
                e["target_patterns"] = list(fresh)
            e["removal_ok"] = (e.get("target") or "") in L.REMOVAL_OK
            out[e["vendor"]] = e
    for vendor, entry in (local or {}).items():
        if vendor not in out:
            e = dict(entry)
            e["source"] = "local-scan"
            out[vendor] = e
    return list(out.values())


def _is_github_slug(r: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", r))


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

    # Rule 1 of the skill: no verified MIT/Apache licence → refuse, no exceptions. A --repo clone
    # has no registry row, so the licence is MEASURED here instead of being assumed.
    lic_spdx = (row or {}).get("license_spdx")
    if row:
        if not row.get("license_ok"):
            print(f"factory_clone: REFUSED — {repo} has no verified MIT/Apache-2.0 license "
                  f"(spdx={row.get('license_spdx')!r}). The pool is permissive-licenses-only.", file=sys.stderr)
            return 4
    elif _is_github_slug(repo):
        lic_spdx, lic_path, lic_ok = L.license_of(repo)
        if not lic_ok:
            print(f"factory_clone: REFUSED — {repo} has no verified MIT/Apache-2.0 license "
                  f"(spdx={lic_spdx!r}, file={lic_path!r}). Permissive licences only — check the "
                  f"licence before cloning anything else.", file=sys.stderr)
            return 4
    else:
        # local path fixture (native path or a file:// URI): it must carry a LICENSE of its own
        probe = repo
        if repo.startswith("file://"):
            from urllib.parse import unquote, urlparse
            probe = unquote(urlparse(repo).path)
            if re.match(r"^/[A-Za-z]:", probe):  # /C:/… on Windows
                probe = probe[1:]
        cand = sorted(Path(probe).glob("LICENSE*")) if Path(probe).is_dir() else []
        if not cand:
            print(f"factory_clone: REFUSED — {repo} is a local path with no LICENSE file. "
                  f"Permissive licences only.", file=sys.stderr)
            return 4
        lic_spdx = cand[0].name

    root = Path(args.root)
    if os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", str(args.root)):
        print(f"factory_clone: --root {args.root!r} is a Windows-style path but this is not Windows — "
              f"pass the projects root explicitly (e.g. --root ~/projects).", file=sys.stderr)
        return 2
    dest = root / args.slug
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
    def _clone(ref: str | None) -> tuple[int, str]:
        cmd = ["clone", "--depth", "1"] + (["--branch", ref] if ref else []) + [url, str(dest)]
        rc_, log_ = git(cmd, dest.parent)
        if rc_ == 0 or not ref:
            return rc_, log_
        # `--branch` only accepts a branch or tag NAME — a commit sha needs fetch + checkout.
        shutil.rmtree(dest, ignore_errors=True)
        rc0, log0 = git(["clone", "--depth", "1", url, str(dest)], dest.parent)
        if rc0 != 0:
            return rc0, log0
        rc1, log1 = git(["fetch", "--depth", "1", "origin", ref], dest)
        if rc1 != 0:
            return rc1, log1
        return git(["checkout", "-q", "--detach", "FETCH_HEAD"], dest)

    rc, log = _clone(args.ref)
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
        "license": {"spdx": lic_spdx, "file": (row or {}).get("license_file")},
        "stack": (row or {}).get("stack"), "shape": (row or {}).get("shape"),
        "canonical": (row or {}).get("canonical"), "canonical_notes": (row or {}).get("canonical_notes"),
        "cloned_at": DB.now(),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    # The map must describe THIS clone, not just the registry row: a --repo clone has no row, and a
    # vendor used only in the template's code/README/.env.example never appears in dep names.
    reg_swaps = _as_entry_list((row or {}).get("swap_map"))
    local_swaps = _scan_clone_for_vendors(dest)
    merged = _merge_swaps(reg_swaps, local_swaps)
    (state / "swap-map.json").write_text(json.dumps({
        "project": args.slug, "generated_at": DB.now(),
        "source": "templates.db + local clone scan" if local_swaps else "templates.db",
        "swaps": merged,
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
| license | {lic_spdx or 'UNVERIFIED'} |
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

    # The commit is cut on the PRISTINE clone — before the install — so no installed artifact
    # (node_modules, .next) can ever enter the project's first commit.
    git(["add", "-A"], dest)
    rc, out = git(["-c", "user.email=factory@local", "-c", "user.name=buildout-factory",
                   "commit", "-q", "-m", f"chore: clone {row['name'] if row else repo} via buildout factory (upstream {commit[:7]})"], dest)

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

    result = {"project": str(dest), "template": row["name"] if row else repo, "commit": commit,
              "swap_map": str(state / "swap-map.json"), "swap_map_entries": len(merged),
              "swap_map_source": "templates.db + local clone scan" if local_swaps else "templates.db",
              "pending": str(dest / "PENDING.md")}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"cloned {repo} -> {dest}\n  upstream commit {commit[:12]}\n  license {lic_spdx}")
        if env_note:
            print(f"  {env_note}")
        if merged:
            print(f"  swap map: {len(merged)} entr{'y' if len(merged) == 1 else 'ies'} "
                  f"({result['swap_map_source']})")
        else:
            print("  swap map: EMPTY — no vendor dependencies were measured for this template.\n"
                  "            swap_check refuses an empty map (exit 3) — fill it first:\n"
                  "              py scripts/template_intake.py --repo <owner/name>")
        print(f"  next: cd {dest} && {runner} install  # then py scripts/swap_check.py --project {dest}")
        print(f"  state: {state}\\  |  mandatory facts: {dest / 'PENDING.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
