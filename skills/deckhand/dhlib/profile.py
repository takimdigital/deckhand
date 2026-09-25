"""The owner, once: ~/.deckhand/profile.json (facts) + ~/.deckhand/vault.env (secrets, chmod 600).

The profile answers the questions every project would otherwise ask again (providers, domain habits,
defaults, languages). Secrets never enter the profile, the chat, or a repo: scripts read the vault
directly, `dh vault list` shows names only, and `dh profile doctor` proves which capabilities are
reachable WITHOUT printing a value — "access before asks".
"""
from __future__ import annotations

import os
import re
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


def profile_path() -> Path:
    return home() / "profile.json"


def vault_path() -> Path:
    return home() / "vault.env"


def load() -> dict:
    return read_json(profile_path(), {}) or {}


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


def set_fields(pairs: list) -> dict:
    prof = load()
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
    write_json(profile_path(), prof)
    return {"changed": changed, "path": str(profile_path())}


# ------------------------------------------------------------------ vault
def vault_read() -> dict:
    p = vault_path()
    out = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.replace("export ", "").strip()] = v.strip().strip('"').strip("'")
    return out


def vault_set(name: str, value: str | None = None) -> dict:
    if not re.match(r"^[A-Z][A-Z0-9_]{1,63}$", name):
        raise DhError("BAD_NAME", "vault names are UPPER_SNAKE_CASE")
    if value is None:
        value = sys.stdin.readline().rstrip("\n") if not sys.stdin.isatty() else __import__("getpass").getpass(f"{name}: ")
    if not value:
        raise DhError("EMPTY", "no value given")
    data = vault_read()
    data[name] = value
    p = vault_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("# deckhand vault — secrets only; never commit, never paste into chat\n" +
                 "\n".join(f"{k}={v}" for k, v in sorted(data.items())) + "\n", encoding="utf-8")
    try:
        os.chmod(p, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return {"stored": name, "names": sorted(data)}


def secret(name: str):
    """Env first (CI / harness secrets), then the vault. Never logged."""
    return os.environ.get(name) or vault_read().get(name)


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
    cf = secret("CLOUDFLARE_API_TOKEN")
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
