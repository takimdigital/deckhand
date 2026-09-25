"""BUILD: four ways in, one result — a project folder that runs locally, with its own git history.

  clone <template>   a pool row (public or yours): shallow clone at the measured commit, fresh
                     history, NOTICE (upstream + commit + licence), .env seeded with LOCAL secrets only
  adopt <path|url>   the owner's existing project, history kept
  scaffold           from scratch: create-next-app + the canonical UI base (tokens, cn, Button)
  compose            a landing page assembled from licensed blocks with the plan's copy (no LLM)
  dev start|stop     run it and prove it answers
"""
from __future__ import annotations

import os
import re
import secrets
import shutil
import signal
import socket
import subprocess
import time
import urllib.request
from pathlib import Path

from .util import ensure_gitignore, DhError, TEMPLATES, TRYON, now, package_json, package_manager, read_json, rmtree, run, slugify, write_json
from . import pool as POOL
from . import state as STATE

LOCAL_SECRET_KEYS = re.compile(r"^(BETTER_AUTH_SECRET|AUTH_SECRET|NEXTAUTH_SECRET|JWT_SECRET|SESSION_SECRET|COOKIE_SECRET|ENCRYPTION_KEY|SECRET_KEY_BASE|PAYLOAD_SECRET)=", re.M)


def _fresh_git(dest: Path, message: str) -> None:
    rmtree(dest / ".git")                                  # read-only git objects on Windows: really gone, or history leaks
    run(["git", "init", "-q"], cwd=dest)
    run(["git", "add", "-A"], cwd=dest)
    run(["git", "-c", "user.name=deckhand", "-c", "user.email=deckhand@localhost", "commit", "-qm", message], cwd=dest)


def seed_env(dest: Path) -> list:
    """.env from .env.example; generate values ONLY for local secrets (never vendor keys)."""
    ex = next((dest / n for n in (".env.example", ".env.local.example", ".env.sample", ".env.template") if (dest / n).exists()), None)
    target = dest / ".env"
    if not ex or target.exists():
        return []
    text = ex.read_text(encoding="utf-8")
    made = []

    def fill(m):
        made.append(m.group(1))
        return f"{m.group(1)}={secrets.token_urlsafe(32)}"
    text = re.sub(r"^(BETTER_AUTH_SECRET|AUTH_SECRET|NEXTAUTH_SECRET|JWT_SECRET|SESSION_SECRET|COOKIE_SECRET|ENCRYPTION_KEY|SECRET_KEY_BASE|PAYLOAD_SECRET)=.*$", fill, text, flags=re.M)
    target.write_text(text, encoding="utf-8")
    gi = dest / ".gitignore"
    g = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if not re.search(r"^\.env$|^\.env\*|^\.env\.local", g, re.M):
        gi.write_text(g.rstrip("\n") + "\n.env\n.env*.local\n", encoding="utf-8")
    return made


def install(dest: Path) -> dict:
    pm = package_manager(dest)
    cmd = {"npm": ["npm", "install", "--no-audit", "--no-fund"], "pnpm": ["pnpm", "install"], "yarn": ["yarn", "install"], "bun": ["bun", "install"]}[pm]
    r = run(cmd, cwd=dest, timeout=1800)
    return {"pm": pm, "ok": r["code"] == 0, "cmd": r["cmd"], "tail": (r["err"] or r["out"])[-600:]}


def _record_base(dest: Path, base: dict, name: str, path: str) -> None:
    ensure_gitignore(dest)                                # every way in keeps deckhand's run logs out of git
    s = STATE.load(dest, required=False)
    if not s:
        STATE.init(dest, name=name, path=path)            # also writes the AGENTS.md cold-start entry
        s = STATE.load(dest)
    else:
        from . import resume as RESUME
        RESUME.agent_entry(dest)
    s["base"] = base
    STATE.save(dest, s)


def clone(name: str, to: Path, do_install: bool = True) -> dict:
    row = next((r for r in POOL.rows() if r["name"] == name), None)
    if not row:
        raise DhError("NO_SUCH_TEMPLATE", f"{name} is not in the pool (dh pool query …)")
    if row.get("license") not in POOL.OK_LICENSES and not (row.get("source") == "mine" and row.get("license") in POOL.OWNER_LICENSES):
        raise DhError("LICENCE_REFUSED", f"{name}: licence {row.get('license')}")
    to = Path(to).resolve()
    if to.exists() and any(to.iterdir()):
        raise DhError("DEST_NOT_EMPTY", f"{to} is not empty — pick a new folder")
    to.parent.mkdir(parents=True, exist_ok=True)
    if row.get("path") and Path(row["path"]).exists():   # a harvested base on this machine
        shutil.copytree(row["path"], to, ignore=shutil.ignore_patterns("node_modules", ".git", ".next", ".deckhand", ".env", ".env.*"))
        commit = "local"
    elif row.get("source") == "mine" and row.get("repo"):  # the owner's private library base, from their GitHub
        from . import github as GH
        GH.clone(row["repo"], to, branch=row.get("branch") or "main")
        commit = run(["git", "rev-parse", "HEAD"], cwd=to)["out"].strip() or "library"
    else:
        url = f"https://github.com/{row['repo']}.git"
        r = run(["git", "clone", "--depth", "1", "--branch", row.get("branch") or "main", url, str(to)], timeout=900)
        if r["code"] != 0:
            raise DhError("CLONE_FAILED", r["err"][-400:])
        commit = run(["git", "rev-parse", "HEAD"], cwd=to)["out"].strip()
        if row.get("commit") and row["commit"] != commit:
            f = run(["git", "fetch", "--depth", "1", "origin", row["commit"]], cwd=to, timeout=300)
            if f["code"] == 0:
                run(["git", "checkout", "-q", row["commit"]], cwd=to)
                commit = row["commit"]
    lic = next((p.name for p in to.iterdir() if p.name.upper().startswith(("LICENSE", "LICENCE"))), None)
    (to / "NOTICE").write_text(
        f"This project started from {row.get('repo') or row['name']} ({row.get('license')}), commit {commit}.\n"
        f"The upstream licence is kept in {lic or 'LICENSE'} — keep this file and that licence in the project.\n", encoding="utf-8")
    made = seed_env(to)
    _fresh_git(to, f"base: {row['name']} @ {commit[:12]} ({row.get('license')})")
    _record_base(to, {"kind": "template", "name": row["name"], "repo": row.get("repo"), "commit": commit, "at": now()}, name=to.name, path="mine" if row.get("source") == "mine" else "pool")
    inst = install(to) if do_install and (to / "package.json").exists() else None
    return {"project": str(to), "template": row["name"], "commit": commit, "local_secrets_generated": made, "install": inst,
            "next": "dh dev start --project " + str(to)}


def adopt(src: str, to: Path | None = None, do_install: bool = False) -> dict:
    if re.match(r"^(https?://|git@)", src):
        dest = Path(to or slugify(src.rstrip("/").split("/")[-1].removesuffix(".git"))).resolve()
        r = run(["git", "clone", src, str(dest)], timeout=1800)
        if r["code"] != 0:
            raise DhError("CLONE_FAILED", r["err"][-400:])
    else:
        dest = Path(src).resolve()
        if not dest.exists():
            raise DhError("NO_SUCH_PATH", str(dest))
        if to:
            shutil.copytree(dest, Path(to), ignore=shutil.ignore_patterns("node_modules", ".next"))
            dest = Path(to).resolve()
    pkg = package_json(dest)
    stack = POOL.detect_stack(pkg, [str(p.relative_to(dest)).replace("\\", "/") for p in dest.rglob("*") if "node_modules" not in p.parts and p.is_file()][:20000])
    _record_base(dest, {"kind": "existing", "source": src, "stack": stack, "at": now()}, name=dest.name, path="existing")
    inst = install(dest) if do_install and (dest / "package.json").exists() else None
    return {"project": str(dest), "stack": stack, "install": inst, "next": "dh dev start"}


def scaffold(to: Path, pm: str = "npm") -> dict:
    to = Path(to).resolve()
    if to.exists() and any(to.iterdir()):
        raise DhError("DEST_NOT_EMPTY", str(to))
    to.parent.mkdir(parents=True, exist_ok=True)
    r = run(["npx", "--yes", "create-next-app@latest", str(to), "--ts", "--tailwind", "--app", "--no-eslint", "--no-src-dir",
             "--import-alias", "@/*", f"--use-{pm}", "--yes", "--disable-git"], timeout=1800)
    if r["code"] != 0:
        raise DhError("SCAFFOLD_FAILED", (r["err"] or r["out"])[-600:])
    base = TEMPLATES / "scaffold"
    for rel in ("components/ui/button.tsx", "lib/utils.ts"):
        (to / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(base / rel, to / rel)
    css = to / "app" / "globals.css"
    css.write_text((base / "app" / "globals.css").read_text(encoding="utf-8"), encoding="utf-8")
    deps = ["clsx", "tailwind-merge", "class-variance-authority", "radix-ui", "lucide-react", "tw-animate-css"]
    ir = run({"npm": ["npm", "install", "--no-audit", "--no-fund"], "pnpm": ["pnpm", "add"], "bun": ["bun", "add"], "yarn": ["yarn", "add"]}[pm] + deps, cwd=to, timeout=1800)
    _fresh_git(to, "base: create-next-app + deckhand UI base (tokens, cn, Button)")
    _record_base(to, {"kind": "scratch", "at": now()}, name=to.name, path="scratch")
    return {"project": str(to), "deps_ok": ir["code"] == 0, "next": "dh compose --sections hero,features,pricing,faq,cta,footer (or build pages from the plan)"}


def compose(root: Path, page: str, sections: list, copy: str | None) -> dict:
    node = shutil.which("node")
    if not node:
        raise DhError("NO_NODE", "node is required for compose")
    argv = [node, str(TRYON / "compose.mjs"), "--project", str(root), "--page", page, "--sections", ",".join(sections)]
    if copy:
        argv += ["--copy", copy]
    r = run(argv, cwd=root, timeout=900)
    try:
        return __import__("json").loads(r["out"].strip().splitlines()[-1])
    except Exception:
        raise DhError("COMPOSE_FAILED", (r["err"] or r["out"])[-800:])


# ------------------------------------------------------------------ dev server
def _free_port(start: int = 3000) -> int:
    for p in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", p)) != 0:
                return p
    raise DhError("NO_PORT", f"no free port in {start}-{start + 49}")


def _answers(url: str) -> int | None:
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return r.status
    except Exception as e:  # noqa: BLE001
        return getattr(e, "code", None)


def serve(root: Path, script: str, port: int, log: Path, wait: int = 180):
    """Start `<pm> run <script> --port N` detached (own process group); wait until it answers < 500.
    Returns (proc, url, status). The caller stops it with kill_tree(proc.pid)."""
    root = Path(root)
    pm = package_manager(root)
    cmd = {"npm": ["npm", "run", script, "--"], "pnpm": ["pnpm", "run", script], "yarn": ["yarn", script], "bun": ["bun", "run", script]}[pm] + ["--port", str(port)]
    log.parent.mkdir(parents=True, exist_ok=True)
    out = open(log, "w")
    kw = {"cwd": str(root), "stdout": out, "stderr": subprocess.STDOUT, "env": {**os.environ, "PORT": str(port)}}
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x00000200          # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
        cmd[0] = shutil.which(cmd[0]) or cmd[0]
    else:
        kw["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **kw)
    finally:
        out.close()                                            # the child keeps its own handle
    url = f"http://localhost:{port}"
    t0 = time.time()
    status = None
    while time.time() - t0 < wait:
        status = _answers(url)
        if status and status < 500:
            break
        if proc.poll() is not None:
            break
        time.sleep(1.5)
    proc.cmd = " ".join(cmd)
    return proc, url, status


def kill_tree(pid: int) -> None:
    if os.name == "nt":
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
    else:
        os.killpg(os.getpgid(pid), signal.SIGTERM)


def dev_start(root: Path, port: int | None = None, wait: int = 180) -> dict:
    root = Path(root)
    info = read_json(root / ".deckhand" / "dev.json", {}) or {}
    if info.get("url") and _answers(info["url"]):
        return {"running": True, **info, "reused": True}
    pkg = package_json(root)
    script = "dev" if "dev" in (pkg.get("scripts") or {}) else "start"
    log = root / ".deckhand" / "dev.log"
    proc, url, status = serve(root, script, port or _free_port(), log, wait)
    info = {"url": url, "pid": proc.pid, "cmd": proc.cmd, "started": now(), "status": status}
    write_json(root / ".deckhand" / "dev.json", info)
    tail = log.read_text(encoding="utf-8", errors="replace")[-1500:]
    if not status or status >= 500:
        return {"running": False, **info, "log_tail": tail, "hint": "read the log tail; `dh learn match --log .deckhand/dev.log` knows past fixes"}
    return {"running": True, **info}


def dev_stop(root: Path) -> dict:
    info = read_json(Path(root) / ".deckhand" / "dev.json", {}) or {}
    pid = info.get("pid")
    if not pid:
        return {"stopped": False, "reason": "not started by dh"}
    try:
        kill_tree(pid)
    except Exception as e:  # noqa: BLE001
        return {"stopped": False, "reason": str(e)}
    return {"stopped": True, "pid": pid}


def dev_status(root: Path) -> dict:
    info = read_json(Path(root) / ".deckhand" / "dev.json", {}) or {}
    return {**info, "answers": _answers(info["url"]) if info.get("url") else None}
