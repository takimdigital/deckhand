#!/usr/bin/env python3
"""template_intake.py — measure a template through GitHub. No cloning by default.

Remote mode (default): repo metadata + license + full file tree + a handful of
key files, all via the GitHub API. Nothing touches the disk, nothing executes.
Deep mode (--deep --yes): clone + install + build + boot in a scratch dir, ONLY
after the user accepted. The boot scorecard is the one fact that cannot be read
remotely.

usage:
  py scripts/template_intake.py --repo wasp-lang/open-saas
  py scripts/template_intake.py --seed data/templates.seed.json
  py scripts/template_intake.py --repo ixartz/Next-js-Boilerplate --deep --yes --scratch D:/_factory/scratch
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _tpl_lib as L  # noqa: E402
import templates_db as DB  # noqa: E402

KEY_FILES = ["package.json", "pyproject.toml", "requirements.txt", "composer.json", "Gemfile",
             "docker-compose.yml", "docker-compose.yaml", "compose.yml", "Dockerfile",
             "README.md", ".env.example", "main.wasp", "prisma/schema.prisma", "components.json",
             "next.config.js", "next.config.mjs", "next.config.ts", "wrangler.toml", "vercel.json"]


def measure(repo: str, ref: str | None = None, want_readme_text: bool = True) -> dict:
    info = L.repo_json(repo)
    if not info or info.get("_error"):
        return {"name": repo.split("/")[-1], "repo": repo, "url": f"https://github.com/{repo}",
                "status": "unverified", "reject_reason": f"repo lookup failed: {info.get('_error') if isinstance(info, dict) else 'not found'}",
                "risk_flags": [{"kind": "lookup-failed", "detail": str(info)[:200] if isinstance(info, dict) else "404"}],
                "evidence": {"source": "github-api", "checked_at": DB.now()}}

    branch = ref or info.get("default_branch") or "main"
    tree = L.branch_tree(repo, branch)
    texts: dict[str, str] = {}
    fetched = []
    for f in KEY_FILES:
        if f in tree or any(t.endswith("/" + f) for t in tree):
            path = f if f in tree else next(t for t in tree if t.endswith("/" + f))
            txt = L.file_text(repo, path, branch)
            if txt is not None:
                texts[f] = txt
                fetched.append(path)

    pkg = L.parse_package_json(texts.get("package.json"))
    # python/non-js manifests feed the same detection blob
    blob_texts = dict(texts)
    stack = L.detect_stack(tree, pkg, blob_texts)
    dep_names = list(L.all_dep_names(pkg).keys())
    for key in ("requirements.txt", "pyproject.toml"):
        if key in texts:
            dep_names += re.findall(r"^([A-Za-z0-9_.\-]+)\s*[=><~!\[]", texts[key], flags=re.M)[:200]
    blob = " ".join([texts.get("README.md") or "", texts.get("docker-compose.yml") or "",
                     texts.get("docker-compose.yaml") or "", texts.get("compose.yml") or "",
                     texts.get(".env.example") or "", " ".join(tree)])
    vendor, selfhost, unclassified, swap_map = L.classify_deps(dep_names, blob)
    shape, shape_src = L.guess_shape(tree, texts.get("README.md") or "",
                                     info.get("description") or "", info.get("topics") or [])
    spdx, lic_path, lic_ok = L.license_of(repo)
    # version sanity: read the declared dep versions so a clone never surprises us
    contribs = L.contributors(repo, limit=100)
    flags = L.risk_flags(info, tree, lic_ok, stack.get("tests"), stack.get("docker"),
                         texts.get("README.md") if want_readme_text else None, contribs)

    rebrand_surface = sorted({
        p for p in tree
        if p.startswith(("src/app/", "app/", "messages/", "locales/", "public/", "src/styles/",
                         "styles/", "src/config/", "config/"))
        and p.lower().endswith((".ts", ".tsx", ".css", ".json", ".svg", ".png", ".webp", ".jpg", ".ico", ".woff2"))
        and any(k in p.lower() for k in ("logo", "icon", "favicon", "globals.css", "theme", "config",
                                        "constant", "site", "brand", "meta", "messages/"))
    })
    locales = stack.get("locales") or []

    return {
        "name": repo.split("/")[-1], "repo": repo, "url": f"https://github.com/{repo}",
        "status": "unverified", "license_spdx": spdx, "license_file": lic_path, "license_ok": 1 if lic_ok else 0,
        "stars": info.get("stargazers_count"), "forks": info.get("forks_count"),
        "open_issues": info.get("open_issues_count"), "pushed_at": (info.get("pushed_at") or "")[:10],
        "archived": 1 if info.get("archived") else 0, "default_branch": branch,
        "size_kb": info.get("size"), "shape": shape, "shape_source": shape_src,
        "stack": stack, "canonical": L.is_canonical(stack)[0], "canonical_notes": L.is_canonical(stack)[1],
        "deps_vendor": vendor, "deps_selfhost": selfhost, "deps_unclassified": unclassified[:40],
        "swap_map": swap_map, "rebrand_surface": rebrand_surface[:40], "risk_flags": flags,
        "evidence": {"source": "github-api (no clone)", "checked_at": DB.now(), "branch": branch,
                     "files_read": fetched, "tree_entries": len(tree), "locales": locales,
                     "license_path": lic_path},
    }


def deep_boot(repo: str, scratch: Path, slug: str | None = None, port: int = 7390,
              timeout_install: int = 1200, timeout_build: int = 900) -> dict:
    """Consent-gated: clone + package-manager install + build + boot. The only
    path in the factory that executes third-party code. Returns boot_* fields."""
    slug = slug or repo.split("/")[-1].lower().replace(".", "-")
    dest = scratch / f"{slug}-boot"
    out = {"boot_install_ok": 0, "boot_build_ok": 0, "boot_start_ok": 0, "boot_tests": "not run",
           "boot_ms": 0, "boot_port": None, "error": None, "dest": str(dest)}
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rc, _, err = L._run(["git", "clone", "--depth", "1", f"https://github.com/{repo}.git", str(dest)], timeout=600)
    if rc != 0:
        out["error"] = f"clone failed: {err[:200]}"
        return out
    runner, install_cmd, build_cmd = "npm", ["npm", "install", "--no-audit", "--no-fund"], ["npm", "run", "build"]
    if (dest / "pnpm-lock.yaml").exists():
        runner, install_cmd = "pnpm", ["pnpm", "install", "--prefer-offline"]
    elif (dest / "yarn.lock").exists():
        runner, install_cmd = "yarn", ["yarn", "install"]
    elif (dest / "bun.lockb").exists() or (dest / "bun.lock").exists():
        runner, install_cmd = "bun", ["bun", "install"]
    if not any((dest / f).exists() for f in ("package.json",)):
        out["error"] = "not a node project — deep boot only implemented for node templates"
        return out
    pkg = L.parse_package_json((dest / "package.json").read_text(encoding="utf-8", errors="ignore"))
    scripts = pkg.get("scripts") or {}
    env_example = dest / ".env.example"
    if env_example.exists() and not (dest / ".env").exists():
        shutil.copy(env_example, dest / ".env")
    rc, log, err = L._run(install_cmd, timeout=timeout_install, cwd=str(dest))
    out["boot_install_ok"] = 1 if rc == 0 else 0
    if rc != 0:
        out["error"] = f"install failed: {(err or log)[-300:]}"
        return out
    if "build" in scripts:
        rc, log, err = L._run([runner, "run", "build"], timeout=timeout_build, cwd=str(dest))
        out["boot_build_ok"] = 1 if rc == 0 else 0
        if rc != 0:
            failed = (err or "") + (log or "")
            vendors = L.vendor_key_failure(failed)
            out["error"] = f"build failed: {failed[-300:]}"
            if vendors:
                out["needs_vendor_keys"] = vendors
            return out
    if "test" in scripts:
        rc, log, err = L._run([runner, "run", "test", "--", "--run"] if runner == "pnpm" else [runner, "test"],
                              timeout=600, cwd=str(dest))
        out["boot_tests"] = "pass" if rc == 0 else "fail"
    start = "start" if "start" in scripts else "dev" if "dev" in scripts else None
    if start:
        env = dict(**__import__("os").environ, PORT=str(port), NODE_ENV="production" if start == "start" else "development")
        try:
            p = subprocess.Popen([runner, "run", start], cwd=str(dest), env=env,
                                 stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            ok = False
            for _ in range(60):
                time.sleep(2)
                try:
                    import urllib.request
                    with urllib.request.urlopen(f"http://localhost:{port}/", timeout=5) as r:
                        ok = r.status < 500
                        break
                except Exception:  # noqa: BLE001
                    if p.poll() is not None:
                        break
            out["boot_start_ok"] = 1 if ok else 0
            out["boot_port"] = port if ok else None
            p.terminate()
            try:
                p.wait(timeout=15)
            except Exception:  # noqa: BLE001
                p.kill()
        except Exception as e:  # noqa: BLE001
            out["error"] = f"start failed: {e}"
    out["boot_ms"] = int((time.time() - t0) * 1000)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="measure a template remotely (no clone) into templates.db")
    ap.add_argument("--repo", help="owner/name")
    ap.add_argument("--seed", help="seed json with templates[]")
    ap.add_argument("--only", help="comma-separated names to filter the seed")
    ap.add_argument("--ref")
    ap.add_argument("--db", default=str(DB.DEFAULT_DB))
    ap.add_argument("--json", action="store_true", help="print the measured record(s) as JSON")
    ap.add_argument("--deep", action="store_true", help="clone+build+boot (executes third-party code)")
    ap.add_argument("--yes", action="store_true", help="consent for --deep")
    ap.add_argument("--scratch", default="D:/_factory/scratch")
    ap.add_argument("--port", type=int, default=7390)
    args = ap.parse_args(argv)

    targets: list[str] = []
    if args.repo:
        targets = [args.repo]
    elif args.seed:
        data = json.loads(Path(args.seed).read_text(encoding="utf-8"))
        rows = data.get("templates", data)
        if args.only:
            keep = {x.strip().lower() for x in args.only.split(",")}
            rows = [r for r in rows if r["name"].lower() in keep or r["url"].split("/")[-1].lower() in keep]
        targets = [r.get("repo") or r["url"].rstrip("/").split("github.com/", 1)[-1] for r in rows]
    else:
        ap.error("need --repo or --seed")

    if args.deep and not args.yes:
        print("refusing --deep without --yes: this clones and executes third-party code. "
              "Ask the user first, then pass --yes.", file=sys.stderr)
        return 3

    con = DB.connect(Path(args.db))
    results = []
    for repo in targets:
        print(f"measuring {repo} (remote)...", flush=True)
        rec = measure(repo, ref=args.ref)
        if args.deep:
            print(f"  deep boot (consent given): cloning into {args.scratch}", flush=True)
            boot = deep_boot(repo, Path(args.scratch), port=args.port)
            rec.update({k: v for k, v in boot.items() if k != "needs_vendor_keys"})
            if boot.get("needs_vendor_keys"):
                rec.setdefault("risk_flags", []).append({
                    "kind": "vendor-keys-required",
                    "detail": "build needs " + ", ".join(boot["needs_vendor_keys"]) + " — swap first, then build",
                })
        rank = None
        seed = con.execute("SELECT rank FROM templates WHERE repo = ? OR url LIKE ?", (repo, f"%{repo}%")).fetchone()
        if seed and seed["rank"]:
            rank = seed["rank"]
        if rank:
            rec["rank"] = rank
        DB.upsert(con, rec)
        results.append(rec)
        lic = rec.get("license_spdx") or "?"
        st = rec.get("stack") or {}
        print(f"  license={lic} ok={rec.get('license_ok')} ★{rec.get('stars')} pushed={rec.get('pushed_at')} "
              f"canonical={rec.get('canonical')} shape={rec.get('shape')}")
        print(f"  stack={st.get('framework')}/{st.get('db')}/{st.get('orm')}/auth:{st.get('auth')} "
              f"docker={st.get('docker')} i18n={st.get('i18n')} rtl={st.get('rtl')} tests={','.join(st.get('tests') or []) or '-'}")
        print(f"  vendor deps: {', '.join(rec.get('deps_vendor') or []) or '-'}")
        flags_s = "; ".join(f"{f['kind']}({f['detail'][:60]})" for f in (rec.get("risk_flags") or [])) or "-"
        print(f"  flags: {flags_s}")
    DB.cmd_export(con, DB.DEFAULT_EXPORT)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
