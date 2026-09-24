#!/usr/bin/env python3
"""_tpl_lib.py — shared Template Factory helpers (stdlib only).

Remote-first by design: everything here reads a repo through the GitHub API.
Nothing is cloned, installed or executed unless a caller explicitly asks for the
deep path (and the user consented). Used by template_intake.py and factory_clone.py.
"""
from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

UA = "buildout-factory/0.8 (+https://github.com/takimdigital)"
API = "https://api.github.com"

# ---------------------------------------------------------------- vendor / selfhost map
# kind=service-to-replace | target = the open-source replacement the factory injects.
VENDOR_MAP: dict[str, dict] = {
    "clerk": {"category": "auth", "target": "better-auth", "patterns": ["@clerk/", "clerkClient", "CLERK_SECRET", "CLERK_PUBLISHABLE"]},
    "next-auth": {"category": "auth", "target": "better-auth", "patterns": ["next-auth", "@auth/core", "Auth.js"]},
    "auth0": {"category": "auth", "target": "better-auth", "patterns": ["auth0"]},
    "okta": {"category": "auth", "target": "better-auth", "patterns": ["@okta/"]},
    "supabase": {"category": "backend", "target": "docker-postgres + better-auth", "patterns": ["@supabase/", "supabase.co"]},
    "firebase": {"category": "backend", "target": "docker-postgres + better-auth", "patterns": ["firebase", "firebaseapp.com"]},
    "neon": {"category": "db", "target": "docker-postgres", "patterns": ["@neondatabase", "neon.tech", "neon("]},
    "planetscale": {"category": "db", "target": "docker-postgres", "patterns": ["@planetscale/"]},
    "mongodb-atlas": {"category": "db", "target": "docker-postgres", "patterns": ["mongodb+srv", "@mongodb-js/", "MONGODB_URI"]},
    "upstash": {"category": "cache", "target": "docker-redis", "patterns": ["@upstash/"]},
    "stripe": {"category": "payments", "target": "keep", "patterns": ["stripe"], "note": "a processor is a service, not a code lock-in: keep it, or replace with the client's local method"},
    "paddle": {"category": "payments", "target": "keep", "patterns": ["paddle"]},
    "lemonsqueezy": {"category": "payments", "target": "keep", "patterns": ["@lemonsqueezy/", "lemonsqueezy"]},
    "polar": {"category": "payments", "target": "keep", "patterns": ["@polar-sh/"]},
    "resend": {"category": "email", "target": "smtp", "patterns": ["resend"]},
    "sendgrid": {"category": "email", "target": "smtp", "patterns": ["@sendgrid/", "sendgrid"]},
    "mailgun": {"category": "email", "target": "smtp", "patterns": ["mailgun"]},
    "postmark": {"category": "email", "target": "smtp", "patterns": ["postmark"]},
    "aws-s3": {"category": "storage", "target": "minio", "patterns": ["@aws-sdk/", "aws-sdk", "AWS_ACCESS_KEY"]},
    "cloudinary": {"category": "storage", "target": "minio", "patterns": ["cloudinary"]},
    "uploadthing": {"category": "storage", "target": "minio", "patterns": ["uploadthing"]},
    "vercel": {"category": "hosting", "target": "coolify (Docker)", "patterns": ["@vercel/", "vercel.json", "VERCEL_"]},
    "sentry": {"category": "observability", "target": "glitchtip or none", "patterns": ["@sentry/", "sentry"]},
    "plausible": {"category": "analytics", "target": "umami", "patterns": ["plausible"]},
    "posthog": {"category": "analytics", "target": "umami", "patterns": ["posthog"]},
    "google-analytics": {"category": "analytics", "target": "umami", "patterns": ["gtag(", "googletagmanager"]},
    "algolia": {"category": "search", "target": "meilisearch", "patterns": ["algoliasearch", "algolia"]},
    "pusher": {"category": "realtime", "target": "socket.io-or-sse", "patterns": ["pusher"]},
    "ably": {"category": "realtime", "target": "socket.io-or-sse", "patterns": ["ably"]},
    "twilio": {"category": "sms", "target": "keep-or-provider-sms", "patterns": ["twilio"], "default_status": "keep"},
    "openai": {"category": "ai", "target": "ollama", "patterns": ["openai"]},
    "launchdarkly": {"category": "flags", "target": "db-backed-flags", "patterns": ["launchdarkly"], "default_status": "own-code"},
    "arcjet": {"category": "security", "target": "middleware or none", "patterns": ["@arcjet/", "arcjet"], "default_status": "own-code"},
}

# The `target` column is prose for humans; the GATE needs identifiers. Any-of: one hit satisfies.
# A target with no entry here (and not in REMOVAL_OK) can never be proven — keep this table aligned
# with references/factory/30-swap.md whenever a vendor is added.
TARGET_PATTERNS: dict[str, list[str]] = {
    "better-auth": ["better-auth", "betterauth"],
    "docker-postgres": ["postgres", "drizzle-orm", "@prisma/client", "pg", "psycopg"],
    "docker-redis": ["redis", "ioredis"],
    "docker-postgres + better-auth": ["better-auth", "postgres"],
    "smtp": ["nodemailer", "smtp", "mailgun", "brevo"],
    "minio": ["minio", "@aws-sdk/client-s3"],
    "umami": ["umami"],
    "meilisearch": ["meilisearch"],
    "socket.io-or-sse": ["socket.io", "eventsource", "text/event-stream"],
    "ollama": ["ollama", "11434"],
    "glitchtip or none": ["glitchtip"],
    "coolify (Docker)": ["dockerfile", "compose"],
    "keep-or-provider-sms": ["twilio"],
}
# Targets the refs explicitly allow to be satisfied by the owner's OWN code or by deletion
# ("glitchtip or none", "middleware or none", "db-backed flags") — absence only, no library.
REMOVAL_OK = {"glitchtip or none", "middleware or none", "db-backed-flags", "keep-or-provider-sms"}
SELFHOST_HINTS = {
    "postgres": ["postgres", "pg", "@prisma/client", "drizzle-orm", "psycopg", "asyncpg", "pgvector"],
    "sqlite": ["sqlite", "better-sqlite3", "libsql"],
    "redis": ["redis", "ioredis"],
    "minio": ["minio"],
    "smtp": ["nodemailer", "smtplib", "mailhog"],
    "docker": ["docker-compose", "Dockerfile"],
    "meilisearch": ["meilisearch"],
    "umami": ["umami"],
    "keycloak": ["keycloak"],
    "ollama": ["ollama"],
}
README_PLACEHOLDERS = ["your-repo", "your-org", "your-username", "your_username", "yourcompany",
                       "example.com", "YOUR_API_KEY", "changeme", "INSERT_", "<owner>", "your-app-name"]

# Build-time env validation (zod/env schemas) makes a template un-buildable without the vendor's
# keys. That is a SWAP input, not a pool rejection: clone -> swap -> build.
VENDOR_ENV_HINTS = {
    "CLERK_SECRET_KEY": "clerk", "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY": "clerk",
    "STRIPE_SECRET_KEY": "stripe", "STRIPE_WEBHOOK_SECRET": "stripe",
    "SENTRY_AUTH_TOKEN": "sentry", "NEXT_PUBLIC_SENTRY_DSN": "sentry",
    "RESEND_API_KEY": "resend", "SENDGRID_API_KEY": "sendgrid", "MAILGUN_API_KEY": "mailgun",
    "NEXT_PUBLIC_POSTHOG_KEY": "posthog", "DATABASE_URL": "database", "NEON_": "neon",
    "UPLOADTHING_SECRET": "uploadthing", "AWS_SECRET_ACCESS_KEY": "aws-s3",
    "ARCJET_KEY": "arcjet", "OPENAI_API_KEY": "openai",
}


def vendor_key_failure(text: str) -> list[str]:
    """Which vendor credentials the failure text names ([] when it is not a credentials problem)."""
    if not text:
        return []
    up = text.upper()
    return sorted({vendor for key, vendor in VENDOR_ENV_HINTS.items()
                   if key.upper() in up and (key in ("DATABASE_URL", "NEON_") or True)})


# ---------------------------------------------------------------- transport
def _run(cmd: list[str], timeout: int = 60, cwd: str | None = None) -> tuple[int, str, str]:
    # Windows: package managers are .cmd shims which CreateProcess does not resolve from bare
    # names ("npm" -> WinError 2). shutil.which applies PATHEXT, so resolve first.
    exe = shutil.which(cmd[0])
    if exe:
        cmd = [exe] + cmd[1:]
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="ignore")
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:  # noqa: BLE001
        return 1, "", f"{type(e).__name__}: {e}"


def gh(path: str, jq: str | None = None, timeout: int = 60) -> object | None:
    """GET an api.github.com path through the gh CLI (authed) or urllib (fallback)."""
    if shutil.which("gh"):
        cmd = ["gh", "api", path] + (["--jq", jq] if jq else [])
        rc, out, _ = _run(cmd, timeout)
        if rc == 0 and out.strip():
            try:
                return json.loads(out) if not jq else out
            except json.JSONDecodeError:
                return out
    url = path if path.startswith("http") else f"{API}/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode("utf-8", "replace")
        return json.loads(body) if not jq else body
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        return {"_error": f"HTTP {e.code}"}
    except Exception as e:  # noqa: BLE001
        return {"_error": f"{type(e).__name__}: {e}"}


def repo_json(repo: str) -> dict:
    return gh(f"repos/{repo}") or {}


def branch_tree(repo: str, ref: str) -> list[str]:
    data = gh(f"repos/{repo}/git/trees/{ref}?recursive=1")
    if not isinstance(data, dict) or "tree" not in data:
        return []
    return [t.get("path", "") for t in data["tree"] if t.get("type") == "blob"]


def file_text(repo: str, path: str, ref: str | None = None) -> str | None:
    """Fetch one file's text without cloning (contents API, base64)."""
    q = f"?ref={ref}" if ref else ""
    data = gh(f"repos/{repo}/contents/{path}{q}")
    if isinstance(data, dict) and data.get("content"):
        try:
            return base64.b64decode(data["content"]).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            return None
    if isinstance(data, list):  # a directory
        return None
    # fallback: raw
    raw = f"https://raw.githubusercontent.com/{repo}/{ref or 'HEAD'}/{path}"
    req = urllib.request.Request(raw, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None


def license_of(repo: str) -> tuple[str | None, str | None, bool]:
    """(spdx, path, ok) — ok means MIT or Apache-2.0."""
    data = gh(f"repos/{repo}/license")
    spdx = path = None
    if isinstance(data, dict) and data.get("license"):
        spdx = (data["license"] or {}).get("spdx_id")
        path = data.get("path")
    if not spdx:
        info = repo_json(repo)
        spdx = ((info.get("license") or {}) or {}).get("spdx_id")
    ok = bool(spdx and spdx in ("MIT", "Apache-2.0"))
    return spdx, path, ok


def contributors(repo: str, limit: int = 100) -> list[dict]:
    data = gh(f"repos/{repo}/contributors?per_page={limit}")
    return data if isinstance(data, list) else []


# ---------------------------------------------------------------- detection
def parse_package_json(text: str | None) -> dict:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        return {}


def all_dep_names(pkg: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for k in ("dependencies", "devDependencies", "peerDependencies", "optionalDependencies"):
        for name, ver in (pkg.get(k) or {}).items():
            out[name.lower()] = str(ver)
    return out


def detect_stack(tree: list[str], pkg: dict, extra_texts: dict[str, str] | None = None) -> dict:
    deps = all_dep_names(pkg)
    paths = [p.lower() for p in tree]
    joined_paths = "\n".join(paths)
    texts = " ".join((extra_texts or {}).values()).lower()
    has = lambda *needles: any(n in deps for n in needles)  # noqa: E731
    path_has = lambda *needles: any(n in joined_paths for n in needles)  # noqa: E731

    fw = "unknown"
    if "wasp" in deps or path_has("main.wasp"):
        fw = "wasp"
    elif has("next") or path_has("next.config."):
        fw = "next"
    elif has("@remix-run/react", "@remix-run/node") or path_has("remix.config", "app/routes"):
        fw = "remix"
    elif has("nuxt"):
        fw = "nuxt"
    elif has("astro"):
        fw = "astro"
    elif has("fastapi") or path_has("backend/app/main.py") or "fastapi" in texts:
        fw = "fastapi"
    elif has("django") or path_has("manage.py"):
        fw = "django"
    elif has("laravel/framework") or path_has("artisan") or "laravel/framework" in texts:
        # A PHP/Laravel repo often ships package.json + vite.config for its asset build, which is
        # exactly what made bagisto read as "react-vite" — the truth is in composer.json.
        fw = "laravel"
    elif has("expo") or has("react-native"):
        # Mobile apps: react-native/expo repos were being labelled "react-vite" too, and a mobile
        # template can never serve a web business — the registry must not blur that.
        fw = "expo"
    elif has("react") or path_has("vite.config"):
        fw = "react-vite"

    db = "unknown"
    if has("@prisma/client", "prisma", "drizzle-orm", "pg", "postgres", "postgresql", "asyncpg", "psycopg", "sqlmodel") or path_has("schema.prisma", "drizzle.config") or "postgres" in texts:
        db = "postgres"
    if has("better-sqlite3", "libsql") or "sqlite" in joined_paths:
        db = "sqlite" if db == "unknown" else db
    if has("mysql2", "mariadb"):
        db = "mysql" if db == "unknown" else db
    if "MONGODB_URI" in texts or has("mongoose", "mongodb"):
        db = "mongodb" if db == "unknown" else db

    orm = "none"
    for name, cand in (("@prisma/client", "prisma"), ("drizzle-orm", "drizzle"), ("sqlmodel", "sqlmodel"),
                       ("sqlalchemy", "sqlalchemy"), ("typeorm", "typeorm"), ("knex", "knex"), ("mongoose", "mongoose")):
        if name in deps or path_has(f"{cand}.config") or (cand in ("sqlmodel", "sqlalchemy") and cand in texts):
            orm = cand
            break

    auth = "none"
    if "better-auth" in deps:
        auth = "better-auth"
    elif any(d.startswith("@clerk/") or d == "clerk" for d in deps):
        auth = "clerk"
    elif "next-auth" in deps or "@auth/core" in deps:
        auth = "next-auth"
    elif any(d.startswith("@supabase/") for d in deps):
        auth = "supabase"
    elif any(d.startswith("@auth0/") or d == "auth0" for d in deps):
        auth = "auth0"
    elif any(d.startswith("lucia") for d in deps):
        auth = "lucia"
    elif path_has("app/(auth)", "auth/") and ("session" in texts or "login" in joined_paths):
        auth = "custom"

    ui = []
    for name, label in (("tailwindcss", "tailwind"), ("@mui/material", "mui"), ("@chakra-ui/react", "chakra"),
                        ("@mantine/core", "mantine"), ("bootstrap", "bootstrap")):
        if name in deps:
            ui.append(label)
    if path_has("components.json"):
        ui.append("shadcn")

    i18n = None
    for name, label in (("next-intl", "next-intl"), ("i18next", "i18next"), ("react-intl", "react-intl"),
                        ("@lingui/core", "lingui")):
        if name in deps:
            i18n = label
            break
    if not i18n and path_has("messages/", "locales/", "i18n/"):
        i18n = "dirs"

    rtl = None
    # a locale segment must be a real segment ("ar.json", "locales/ar/x.json") —
    # "calendar.json"/"cache.json" must NOT read as Arabic/Hebrew
    LOCALE_SEG = re.compile(r"(?:^|/)(ar|he|fa|ur)(?:\.(?:json|ts|js|po|ya?ml|php)|/|$)")
    if any(LOCALE_SEG.search(p) for p in paths):
        rtl = True
    locales = sorted({p.split("/")[-1].split(".")[0] for p in paths
                      if p.startswith(("messages/", "locales/", "src/messages/", "src/locales/")) and p.endswith((".json", ".ts", ".po"))})

    jobs = [n for n in ("bullmq", "inngest", "@trigger.dev/sdk", "celery", "agenda", "bree") if n in deps]
    tests = [n for n in ("playwright", "@playwright/test", "vitest", "jest", "cypress", "pytest") if n in deps]
    if "pytest" in texts and "pytest" not in tests:
        tests.append("pytest")

    pkg_manager = "unknown"
    for name, label in (("pnpm-lock.yaml", "pnpm"), ("package-lock.json", "npm"), ("yarn.lock", "yarn"),
                        ("bun.lockb", "bun"), ("bun.lock", "bun")):
        if name in joined_paths:
            pkg_manager = label
            break
    if pkg_manager == "unknown" and path_has("poetry.lock", "requirements.txt"):
        pkg_manager = "pip/poetry"

    return {
        "framework": fw, "db": db, "orm": orm, "auth": auth, "ui": sorted(set(ui)),
        "i18n": i18n, "rtl": bool(rtl), "locales": locales, "jobs": jobs, "tests": sorted(set(tests)),
        "docker": bool(path_has("dockerfile", "docker-compose.yml", "compose.yml", "compose.yaml")),
        "admin": bool(path_has("admin/", "dashboard/")),
        "package_manager": pkg_manager,
        "lang": ("python" if fw in ("fastapi", "django") else "php" if fw == "laravel" else "typescript" if fw in ("next", "remix", "wasp", "nuxt", "astro", "react-vite", "expo") else "unknown"),
    }


_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


def tokens_of(blob_low: str) -> set[str]:
    """Word tokens of a lowercased blob. `_` and `-` split, so env-var names work:
    `next_public_posthog_key` must match the vendor `posthog`, while `probably` must not match
    `ably`."""
    return set(_TOKEN_SPLIT.split(blob_low))


def word_hit(needle: str, blob_low: str, tokens: set[str] | None = None) -> bool:
    """Substring for SDK-shaped patterns ('@clerk/', 'socket.io'); whole token for plain words."""
    if re.search(r"[^a-z0-9]", needle):
        return needle in blob_low
    return needle in (tokens if tokens is not None else tokens_of(blob_low))


def classify_deps(dep_names: list[str], config_texts: str, prose_texts: str = "") -> tuple[list, list, list, dict, list]:
    """(vendor, selfhost, unclassified, swap_map_draft, mentioned_only_in_prose).

    A vendor is a FACT about the code: it must appear in the dependency list or in a config file
    (`.env.example`, compose, workflow). A README that name-drops a service is not a dependency —
    conflating the two is how a pool acquires vendors that do not exist.
    """
    low = [d.lower() for d in dep_names]
    strong = (config_texts + " " + " ".join(low)).lower()
    prose = (prose_texts or "").lower()
    strong_tokens, prose_tokens = tokens_of(strong), tokens_of(prose)
    vendor, selfhost, unclassified, mentioned = [], [], [], []
    swap_map: dict[str, dict] = {}
    for key, spec in VENDOR_MAP.items():
        pats = [p.lower() for p in spec["patterns"]]
        if any(word_hit(p, strong, strong_tokens) for p in pats):
            vendor.append(key)
            swap_map[key] = {
                "vendor": key, "category": spec["category"], "target": spec["target"],
                "patterns": spec["patterns"],
                "target_patterns": TARGET_PATTERNS.get(spec["target"], []),
                "removal_ok": spec["target"] in REMOVAL_OK,
                "status": spec.get("default_status") or ("keep" if spec["target"] == "keep" else "pending"),
                "note": spec.get("note", ""),
                "verified": False,
            }
        elif any(word_hit(p, prose, prose_tokens) for p in pats):
            mentioned.append(key)
    for key, needles in SELFHOST_HINTS.items():
        if any(word_hit(n.lower(), strong, strong_tokens) for n in needles):
            selfhost.append(key)
    for d in low:
        if d in vendor or any(v in d for v in vendor):
            continue
        if d.startswith(("@types/", "@radix-ui/", "eslint", "typescript", "prettier")):
            continue
        unclassified.append(d)
    return (sorted(set(vendor)), sorted(set(selfhost)), sorted(set(unclassified))[:80],
            swap_map, sorted(set(mentioned)))


SHAPE_SIGNALS = {
    "marketplace": {"strong": ["marketplace", "multi-vendor", "multivendor", "two-sided", "sellers and buyers"],
                    "weak": ["listings", "vendor", "booking request", "offers"]},
    "booking": {"strong": ["booking system", "appointment scheduling", "reservations", "scheduling platform"],
                "weak": ["calendar", "availability", "time slots", "schedule"]},
    "catalogue": {"strong": ["ecommerce", "e-commerce", "storefront", "shopping cart"],
                  "weak": ["products", "cart", "checkout", "catalog", "shop"]},
    "saas": {"strong": ["saas boilerplate", "saas starter", "saas starter kit", "multi-tenant saas", "subscription business"],
             "weak": ["subscription", "pricing", "plans", "credits", "billing", "teams", "usage-based",
                      "boilerplate", "starter kit", "starter template"]},
    "internal": {"strong": ["internal tool", "admin panel"], "weak": ["crm", "erp", "back-office"]},
    "leadgen": {"strong": ["landing page", "marketing website"], "weak": ["portfolio", "agency site"]},
}


def guess_shape(tree: list[str], texts: str, description: str = "", topics: list[str] | None = None) -> tuple[str, str]:
    blob = " ".join([description or "", " ".join(topics or []), texts or "", "\n".join(tree)]).lower()
    best, best_score, best_hits = "unknown", 0, []
    for shape, sig in SHAPE_SIGNALS.items():
        hits = [k for k in sig["strong"] if k in blob]
        weak = [k for k in sig["weak"] if k in blob]
        score = 2 * len(hits) + len(weak)
        if score > best_score:
            best, best_score, best_hits = shape, score, (hits + weak)[:4]
    if best_score >= 3:
        return best, "heuristic:" + ",".join(best_hits)
    return "unknown", "heuristic:no signal"


def risk_flags(info: dict, tree: list[str], license_ok: bool, tests: list, docker: bool,
               readme: str | None, contribs: list[dict]) -> list[dict]:
    flags: list[dict] = []
    pushed = (info.get("pushed_at") or "")[:10]
    if info.get("archived"):
        flags.append({"kind": "archived", "detail": "repo archived upstream"})
    if pushed:
        try:
            import datetime as dt
            age = (dt.date.today() - dt.date.fromisoformat(pushed)).days
            if age > 365:
                flags.append({"kind": "stale", "detail": f"last push {age} days ago"})
        except Exception:  # noqa: BLE001
            pass
    if not license_ok:
        flags.append({"kind": "license", "detail": "no MIT/Apache-2.0 license found"})
    if not tests:
        flags.append({"kind": "no-tests", "detail": "no test runner detected"})
    if not docker:
        flags.append({"kind": "no-docker", "detail": "no Dockerfile/compose"})
    if readme:
        hits = [p for p in README_PLACEHOLDERS if p.lower() in readme.lower()]
        if hits:
            flags.append({"kind": "readme-placeholders", "detail": ", ".join(sorted(set(hits))[:5])})
    if contribs:
        total = sum(c.get("contributions", 0) for c in contribs) or 1
        top = max(contribs, key=lambda c: c.get("contributions", 0))
        share = top.get("contributions", 0) / total
        if share > 0.9 and len(contribs) > 1:
            flags.append({"kind": "bus-factor", "detail": f"{top.get('login')} owns {share:.0%} of commits"})
    return flags


def is_canonical(stack: dict) -> tuple[int, str]:
    notes = []
    ok = True
    if stack.get("framework") != "next":
        ok = False
        notes.append(f"framework={stack.get('framework')} (canonical: next)")
    if stack.get("db") not in ("postgres", "postgresql"):
        ok = False
        notes.append(f"db={stack.get('db')} (canonical: postgres)")
    if stack.get("auth") not in ("better-auth", "none", "custom"):
        ok = False
        notes.append(f"auth={stack.get('auth')} -> swap to better-auth")
    if not stack.get("docker"):
        notes.append("no docker/compose (Coolify prefers a Dockerfile or nixpacks)")
    return (1 if ok else 0), "; ".join(notes)
