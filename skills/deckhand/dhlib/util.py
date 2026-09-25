"""Shared plumbing for the dh control plane (stdlib only, Python 3.9+)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent          # .../skills/deckhand
DATA = SKILL / "data"
REFS = SKILL / "references"
TEMPLATES = SKILL / "templates"
TRYON = SKILL / "tryon"

# one secret policy for every scanner and for log redaction (data/secrets.json, shared with try-on)
SECRETS = json.loads((DATA / "secrets.json").read_text(encoding="utf-8"))
SECRET_RX = re.compile("|".join(f"(?:{v['rx']})" for v in SECRETS["values"]))
SECRET_STRICT_RX = re.compile("|".join(f"(?:{v['rx']})" for v in SECRETS["values"] + SECRETS["strict_extra"]))
SECRET_FILE_RX = re.compile(SECRETS["files"])
_REDACT_CTX = [re.compile(r"(?i)(\bauthorization:\s*(?:bearer|basic|token)\s+)[^\s'\"]+"),
               re.compile(r"(?i)([?&](?:token|access_token|api_key|apikey|key|secret|password)=)[^&\s'\"]+"),
               re.compile(r"(\b[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|PRIVATE_KEY)=)[^\s'\"]+"),
               re.compile(r"(://[^/\s:@]+:)[^@\s/]+(@)")]


def home() -> Path:
    """~/.deckhand (DECKHAND_HOME overrides) — the owner's portable state."""
    return Path(os.environ.get("DECKHAND_HOME") or (Path.home() / ".deckhand"))


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def today() -> str:
    return time.strftime("%Y-%m-%d")


def read_json(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(p: Path, obj) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, p)


def append_jsonl(p: Path, obj) -> None:
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(p: Path) -> list:
    p = Path(p)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                continue
    return out


def emit(obj, code: int = 0):
    """Machine-first output: exactly one JSON object on stdout."""
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()
    return code


class DhError(Exception):
    def __init__(self, code: str, message: str, /, **extra):       # positional-only: extra may carry its own "code"
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


def redact(text: str, values=()) -> str:
    """Credentials out of anything we write to disk (run logs, failures, autopsy reports): the shared patterns,
    secret-looking assignments/headers/URL parts, and every exact value the caller knows is secret (the vault)."""
    if not text:
        return text
    for v in sorted({v for v in values if v and len(v) >= 8}, key=len, reverse=True):
        text = text.replace(v, "***")
    text = SECRET_STRICT_RX.sub("***", text)
    for rx in _REDACT_CTX:
        text = rx.sub(lambda m: m.group(1) + "***" + (m.group(2) if rx.groups > 1 else ""), text)
    return text


def redact_obj(obj, values=()):
    """redact() over every string of a JSON-like structure (a report before it is written anywhere)."""
    if isinstance(obj, str):
        return redact(obj, values)
    if isinstance(obj, list):
        return [redact_obj(x, values) for x in obj]
    if isinstance(obj, tuple):
        return tuple(redact_obj(x, values) for x in obj)
    if isinstance(obj, dict):
        return {k: redact_obj(v, values) for k, v in obj.items()}
    return obj


GITIGNORE_MARK = "# deckhand: run logs and local state"
GITIGNORE_BLOCK = GITIGNORE_MARK + """ (they can hold command output — never commit them)
.deckhand/runs.jsonl
.deckhand/failures.jsonl
.deckhand/*.log
.deckhand/dev.json
.deckhand/autopsy/
.deckhand/tryon/
"""
# probe path -> what to show (a directory is probed through a file inside it)
RUNTIME_STATE = {".deckhand/runs.jsonl": ".deckhand/runs.jsonl", ".deckhand/failures.jsonl": ".deckhand/failures.jsonl",
                 ".deckhand/dev.log": ".deckhand/*.log", ".deckhand/dev.json": ".deckhand/dev.json",
                 ".deckhand/autopsy/r.md": ".deckhand/autopsy/", ".deckhand/tryon/s.json": ".deckhand/tryon/"}


def ensure_gitignore(root: Path) -> bool:
    """Keep deckhand's run logs out of the owner's git history. Idempotent; returns True when it wrote."""
    gi = Path(root) / ".gitignore"
    text = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if GITIGNORE_MARK in text:
        return False
    gi.parent.mkdir(parents=True, exist_ok=True)
    gi.write_text((text.rstrip("\n") + "\n\n" if text.strip() else "") + GITIGNORE_BLOCK, encoding="utf-8")
    return True


def which(cmd: str):
    """Resolve a launcher to a real executable (Windows PATH carries npm.cmd, not npm)."""
    return shutil.which(cmd)


def rmtree(path) -> None:
    """Delete a tree even where files are read-only (git objects on Windows); a no-op when missing."""
    import stat

    def fix(func, p, _):
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except FileNotFoundError:
            pass
    if not Path(path).exists():
        return
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=fix)
    else:
        shutil.rmtree(path, onerror=fix)


def run(argv: list, cwd=None, timeout: int = 900, env=None, check=False) -> dict:
    exe = which(argv[0]) or argv[0]
    t0 = time.time()
    try:
        p = subprocess.run([exe, *argv[1:]], cwd=str(cwd) if cwd else None, capture_output=True, text=True,
                           timeout=timeout, env={**os.environ, **(env or {})}, encoding="utf-8", errors="replace")
        res = {"cmd": " ".join(argv), "code": p.returncode, "out": p.stdout[-6000:], "err": p.stderr[-6000:],
               "ms": int((time.time() - t0) * 1000)}
    except FileNotFoundError:
        res = {"cmd": " ".join(argv), "code": 127, "out": "", "err": f"{argv[0]}: not found on PATH", "ms": 0}
    except subprocess.TimeoutExpired as e:
        res = {"cmd": " ".join(argv), "code": 124, "out": str(e.stdout or "")[-3000:], "err": "timeout", "ms": timeout * 1000}
    if check and res["code"] != 0:
        raise DhError("COMMAND_FAILED", f"{res['cmd']} -> exit {res['code']}", result=res)
    return res


def project_root(p=None) -> Path:
    """The project: --project, else the nearest parent with .deckhand/ or package.json, else cwd."""
    if p:
        return Path(p).resolve()
    cur = Path.cwd().resolve()
    for d in [cur, *cur.parents]:
        if (d / ".deckhand" / "run.json").exists():
            return d
    for d in [cur, *cur.parents]:
        if (d / "package.json").exists() or (d / "pyproject.toml").exists():
            return d
    return cur


def slugify(s: str, n: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower()
    return s[:n] or "project"


def package_json(root: Path) -> dict:
    return read_json(Path(root) / "package.json", {}) or {}


def package_manager(root: Path) -> str:
    root = Path(root)
    for lock, pm in (("pnpm-lock.yaml", "pnpm"), ("bun.lockb", "bun"), ("bun.lock", "bun"), ("yarn.lock", "yarn"), ("package-lock.json", "npm")):
        if (root / lock).exists():
            return pm
    return "npm"


def pm_run(root: Path, script: str) -> list:
    pm = package_manager(root)
    return {"npm": ["npm", "run", script], "pnpm": ["pnpm", "run", script], "yarn": ["yarn", script], "bun": ["bun", "run", script]}[pm]


def git_files(root: Path) -> list:
    """Tracked + untracked-not-ignored files (falls back to a walk without node_modules/.git)."""
    root = Path(root)
    r = run(["git", "ls-files", "-co", "--exclude-standard"], cwd=root, timeout=60)
    if r["code"] == 0 and r["out"].strip():
        return [root / l for l in r["out"].splitlines() if l.strip()]
    out = []
    skip = {"node_modules", ".git", ".next", "dist", "build", ".deckhand", ".turbo", ".vercel", "__pycache__"}
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in skip]
        out += [Path(dp) / f for f in fns]
    return out


TEXT_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".json", ".md", ".mdx", ".css", ".scss", ".html", ".txt",
            ".yml", ".yaml", ".toml", ".env", ".example", ".py", ".sql", ".prisma", ".svg", ".xml", ".vue", ".svelte", ".astro"}


def is_text(p: Path) -> bool:
    return p.suffix.lower() in TEXT_EXT or p.name in (".env.example", "Dockerfile", "README", "LICENSE")
