"""The owner, once: ~/.deckhand/profile.json (facts) + ~/.deckhand/vault.env (secrets, chmod 600) — plus a
per-project layer: <project>/.deckhand/profile.json + <project>/.deckhand/vault.env (gitignored, never pushed).

The profile answers the questions every project would otherwise ask again (providers, domain habits,
defaults, languages). A project's own layer overrides the machine's for that project only. A project made
for a CLIENT (`dh init --for client`) keeps its settings and secrets in its own layer by default, so client
A's keys can never be used in client B's project; the owner's machine-wide keys stay available as fallback.
Lookup: environment → project vault → machine vault → v1's ops keyring.
Secrets never enter the profile, the chat, or a repo: scripts read the vault directly, `dh vault list` shows
names only, and `dh profile doctor` proves which capabilities are reachable WITHOUT printing a value.
"""
from __future__ import annotations

import os
import re
import shlex
import stat
import sys
import urllib.request
from pathlib import Path

from .util import DhError, home, now, read_json, write_json, which, run

FIELDS = {
    "owner.name": "how the owner wants to be addressed",
    "owner.languages": "languages the owner reads (comma list)",
    "owner.timezone": "IANA zone, e.g. Africa/Casablanca",
    "defaults.mode": "phased | auto",
    "defaults.hosting": "vps | free-preview",
    "defaults.projects_root": "where new projects are created",
    "defaults.package_manager": "npm | pnpm | bun",
    "vps.provider": "hostinger | hetzner | contabo | oracle-free | other",
    "vps.ip": "server IPv4 (not secret)",
    "vps.ssh_user": "usually root",
    "coolify.url": "https://coolify.example.com (or the SSH-tunnel URL)",
    "dns.provider": "cloudflare | registrar",
    "domain.default": "a domain the owner owns (optional)",
    "github.user": "GitHub handle for new repos",
    "email.provider": "resend | mailgun | brevo | smtp",
    "notify.channel": "telegram | discord | email | webhook (where bots report)",
}
SECRET_NAMES = ("COOLIFY_TOKEN", "CLOUDFLARE_API_TOKEN", "HOSTINGER_API_TOKEN", "GITHUB_TOKEN", "RESEND_API_KEY",
                "MAILGUN_API_KEY", "BREVO_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "DISCORD_WEBHOOK_URL",
                "NOTIFY_WEBHOOK_URL", "B2_KEY_ID", "B2_APP_KEY", "TIGRIS_ACCESS_KEY_ID", "TIGRIS_SECRET_ACCESS_KEY",
                "STRIPE_SECRET_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SMTP_URL")


_PROJECT: Path | None = None      # the project whose layer applies (set by the CLI for every command)


def use_project(root) -> None:
    global _PROJECT
    _PROJECT = Path(root) if root and (Path(root) / ".deckhand").is_dir() else None


def profile_path() -> Path:
    return home() / "profile.json"


def vault_path() -> Path:
    return home() / "vault.env"


def project_profile_path() -> Path | None:
    return _PROJECT / ".deckhand" / "profile.json" if _PROJECT else None


def project_vault_path() -> Path | None:
    return _PROJECT / ".deckhand" / "vault.env" if _PROJECT else None


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def project_profile() -> dict:
    p = project_profile_path()
    return (read_json(p, {}) or {}) if p else {}


def scope() -> str:
    """"client" when this project was started for a client: its settings and secrets stay in the project."""
    return "client" if project_profile().get("scope") == "client" else "me"


def set_scope(root, who: str) -> str:
    """`dh init --for me|client`: a client project keeps its own settings and secrets (.deckhand/, gitignored)."""
    if who not in ("me", "client"):
        raise DhError("BAD_SCOPE", "--for me | client")
    p = Path(root) / ".deckhand" / "profile.json"
    prof = read_json(p, {}) or {}
    if prof.get("scope", "me") != who:
        prof["scope"] = who
        prof["updated"] = now()
        write_json(p, prof)
    return who


def load() -> dict:
    return _merge(read_json(profile_path(), {}) or {}, project_profile())


def _target(where: str | None, kind: str) -> Path:
    here = where == "project" or (where is None and scope() == "client")
    if here:
        p = project_profile_path() if kind == "profile" else project_vault_path()
        if not p:
            raise DhError("NO_PROJECT", "no project here (.deckhand/) — run inside the project, or pass --project")
        return p
    return profile_path() if kind == "profile" else vault_path()


def _set(d: dict, dotted: str, value):
    cur = d
    parts = dotted.split(".")
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    cur[parts[-1]] = value


def _get(d: dict, dotted: str):
    cur = d
    for p in dotted.split("."):
        if not isinstance(cur, dict) or p not in cur:
            return None
        cur = cur[p]
    return cur


SECRETISH = re.compile(r"(token|secret|password|passwd|api[_-]?key|private)", re.I)


def set_fields(pairs: list, where: str | None = None) -> dict:
    """Machine profile by default; the project's own layer with where="project" (default in a client project)."""
    target = _target(where, "profile")
    prof = read_json(target, {}) or {}
    changed = {}
    for pair in pairs:
        if "=" not in pair:
            raise DhError("BAD_PAIR", f"expected key=value, got {pair!r}")
        k, v = pair.split("=", 1)
        if SECRETISH.search(k):
            raise DhError("SECRET_IN_PROFILE", f"{k} looks like a secret — use `dh vault set {k.upper()}` instead")
        val = [x.strip() for x in v.split(",")] if k.endswith(("languages", "features")) else v
        _set(prof, k.strip(), val)
        changed[k] = val
    prof["updated"] = now()
    write_json(target, prof)
    return {"changed": changed, "path": str(target), "scope": "project" if target != profile_path() else "machine"}


# ------------------------------------------------------------------ vault
def vault_read() -> dict:
    """Every stored secret this project can use (machine vault, then the project's own, which wins)."""
    out = _vault_file(vault_path())
    pv = project_vault_path()
    if pv:
        out.update(_vault_file(pv))
    return out


def vault_names() -> dict:
    pv = project_vault_path()
    return {"machine": sorted(_vault_file(vault_path())), "project": sorted(_vault_file(pv)) if pv else []}


def _vault_file(p) -> dict:
    out = {}
    if not p or not Path(p).exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.replace("export ", "").strip()] = _unquote(v.strip())
    return out


def _unquote(v: str) -> str:
    try:
        parts = shlex.split(v, posix=True)
        return parts[0] if len(parts) == 1 else v
    except ValueError:
        return v.strip('"').strip("'")


def _quote(v: str) -> str:
    """Single-quoted, so sourcing the vault in a shell never executes or splits a value (`1|abc`, `$x`, spaces)."""
    return "'" + v.replace("'", "'\\''") + "'"


def legacy_home() -> Path:
    return Path(os.environ.get("VPS_OPS_HOME") or (Path.home() / ".vps-ops"))


def legacy_read() -> dict:
    """v1's ops keyring (~/.vps-ops/secrets/*.env.sh) — read-only compatibility, so existing servers keep working."""
    out = {}
    d = legacy_home() / "secrets"
    for f in sorted(d.glob("*.sh")) if d.is_dir() else []:
        for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
            m = re.match(r"^\s*(?:export\s+)?([A-Z][A-Z0-9_]*)=(.*)$", line)
            if m and m.group(1) not in out:
                out[m.group(1)] = _unquote(m.group(2).strip())
    return out


def vault_set(name: str, value: str | None = None, where: str | None = None) -> dict:
    if not re.match(r"^[A-Z][A-Z0-9_]{1,63}$", name):
        raise DhError("BAD_NAME", "vault names are UPPER_SNAKE_CASE")
    if value is None:
        value = sys.stdin.readline().rstrip("\n") if not sys.stdin.isatty() else __import__("getpass").getpass(f"{name}: ")
    if not value:
        raise DhError("EMPTY", "no value given")
    p = _target(where, "vault")
    data = _vault_file(p)                      # only this layer is rewritten: a client's secret never lands elsewhere
    data[name] = value
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# deckhand vault — secrets only; never commit, never paste into chat\n" +
                 "\n".join(f"{k}={_quote(v)}" for k, v in sorted(data.items())) + "\n", encoding="utf-8")
    try:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return {"stored": name, "names": sorted(data), "scope": "project" if p != vault_path() else "machine"}


def secret(name: str):
    """Env first (CI / harness secrets), then this project's vault, the machine vault, v1's ops keyring. Never logged."""
    pv = project_vault_path()
    return (os.environ.get(name) or (_vault_file(pv).get(name) if pv else None) or _vault_file(vault_path()).get(name)
            or legacy_read().get(name))


# ------------------------------------------------------------------ doctor
def _probe(url: str, headers=None, timeout=8):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "deckhand-doctor/2", **(headers or {})})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status
    except Exception as e:  # noqa: BLE001
        return getattr(e, "code", None) or str(e)[:80]


def doctor(online: bool = True) -> dict:
    prof = load()
    have = {n: bool(secret(n)) for n in SECRET_NAMES}
    tools = {t: bool(which(t)) for t in ("git", "node", "npm", "pnpm", "bun", "gh", "ssh", "docker", "python3")}
    caps = {}
    cu, ct = _get(prof, "coolify.url") or os.environ.get("COOLIFY_URL"), secret("COOLIFY_TOKEN")
    if cu and ct and online:
        st = _probe(cu.rstrip("/") + "/api/v1/version", {"Authorization": f"Bearer {ct}"})
        caps["coolify"] = {"ok": st == 200, "evidence": f"GET /api/v1/version -> {st}"}
    else:
        caps["coolify"] = {"ok": False, "evidence": "coolify.url + COOLIFY_TOKEN not both set"}
    cf = secret("CLOUDFLARE_API_TOKEN") or secret("CF_API_TOKEN")          # CF_API_TOKEN = v1's name
    if cf and online:
        st = _probe("https://api.cloudflare.com/client/v4/user/tokens/verify", {"Authorization": f"Bearer {cf}"})
        caps["cloudflare"] = {"ok": st == 200, "evidence": f"tokens/verify -> {st}"}
    else:
        caps["cloudflare"] = {"ok": False, "evidence": "CLOUDFLARE_API_TOKEN not set"}
    if tools["gh"]:
        r = run(["gh", "auth", "status"], timeout=20)
        caps["github"] = {"ok": r["code"] == 0, "evidence": "gh auth status -> " + str(r["code"])}
    else:
        caps["github"] = {"ok": bool(secret("GITHUB_TOKEN")), "evidence": "gh not installed; GITHUB_TOKEN " + ("set" if secret("GITHUB_TOKEN") else "missing")}
    ip = _get(prof, "vps.ip")
    caps["vps"] = {"ok": bool(ip), "evidence": f"vps.ip={ip}" if ip else "no vps.ip in profile"}
    caps["notify"] = {"ok": bool(secret("TELEGRAM_BOT_TOKEN") or secret("DISCORD_WEBHOOK_URL") or secret("NOTIFY_WEBHOOK_URL") or secret("SMTP_URL")),
                      "evidence": "a bot can report somewhere" if any(have[n] for n in ("TELEGRAM_BOT_TOKEN", "DISCORD_WEBHOOK_URL", "NOTIFY_WEBHOOK_URL", "SMTP_URL")) else "no notification channel secret"}
    missing_fields = [k for k in ("owner.name", "defaults.mode", "defaults.hosting") if _get(prof, k) is None]
    asks = []
    if not caps["coolify"]["ok"]:
        asks.append("Coolify: dashboard → Keys & Tokens → API tokens → create (root) → `dh vault set COOLIFY_TOKEN`")
    if not caps["cloudflare"]["ok"]:
        asks.append("Cloudflare: My Profile → API Tokens → Create (Zone.DNS:Edit + Email Routing) → `dh vault set CLOUDFLARE_API_TOKEN`")
    return {"profile": str(profile_path()), "exists": profile_path().exists(), "missing_fields": missing_fields,
            "tools": tools, "secrets_present": [k for k, v in have.items() if v], "capabilities": caps,
            "one_batched_ask": asks}
