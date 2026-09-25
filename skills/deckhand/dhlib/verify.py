"""REVIEW: one command, evidence rows, a red row blocks the deploy gate.

Rows: typecheck · lint (advisory) · build · prod-clean (no try-on stamp in the build) · tryon-closed ·
secrets · leaks/honesty · routes (every planned static route + every internal link on the home page
answers < 400) · a11y basics (advisory) · dependency audit (advisory).
Writes .deckhand/verify.json + .deckhand/VERIFY.md.
"""
from __future__ import annotations

import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

from .util import git_files, is_text, now, package_json, pm_run, read_json, run, write_json
from . import brand as BRAND

SECRET_RX = re.compile(r"(sk_live_[0-9a-zA-Z]{10,}|rk_live_[0-9a-zA-Z]{10,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|AIza[0-9A-Za-z_-]{35}|re_[A-Za-z0-9]{20,}_[A-Za-z0-9]{10,})")


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith("/") and not href.startswith("//"):
                self.links.add(href.split("#")[0].split("?")[0] or "/")


def _get(url: str):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "deckhand-verify/2"})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(400_000).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        return getattr(e, "code", None) or 0, ""


def run_verify(root: Path, url: str | None = None, skip: tuple = (), allow: tuple = ()) -> dict:
    root = Path(root)
    rows = []

    def row(check, ok, detail, blocking=True, evidence=None):
        rows.append({"check": check, "ok": bool(ok), "blocking": blocking, "detail": detail, **({"evidence": evidence} if evidence else {})})

    pkg = package_json(root)
    scripts = pkg.get("scripts") or {}
    if "typecheck" not in skip and (root / "tsconfig.json").exists():
        r = run(["npx", "--no-install", "tsc", "--noEmit", "-p", "."], cwd=root, timeout=900)
        errs = len(re.findall(r"error TS\d+", r["out"] + r["err"]))
        row("typecheck", r["code"] == 0, f"{errs} TypeScript errors" if r["code"] else "tsc --noEmit clean", evidence=(r["out"] or r["err"])[-800:] if r["code"] else None)
    if "lint" not in skip and "lint" in scripts:
        r = run(pm_run(root, "lint"), cwd=root, timeout=900)
        row("lint", r["code"] == 0, "lint clean" if r["code"] == 0 else "lint reported problems", blocking=False, evidence=(r["out"] or r["err"])[-600:] if r["code"] else None)
    if "build" not in skip and "build" in scripts:
        r = run(pm_run(root, "build"), cwd=root, timeout=1800)
        row("build", r["code"] == 0, "production build ok" if r["code"] == 0 else "build failed", evidence=(r["err"] or r["out"])[-1200:] if r["code"] else None)
        out_dirs = [root / d for d in (".next", "dist", "build", "out") if (root / d).is_dir()]
        stamped = []
        for d in out_dirs:
            for p in d.rglob("*"):
                if p.is_file() and "/dev/" not in str(p).replace("\\", "/") and p.suffix in (".js", ".html", ".json") and p.stat().st_size < 5_000_000:
                    try:
                        if 'data-dh="' in p.read_text(encoding="utf-8", errors="ignore"):
                            stamped.append(str(p.relative_to(root)))
                    except Exception:
                        pass
        row("prod-clean", not stamped, "no try-on stamp in the production output" if not stamped else f"{len(stamped)} built files carry dev stamps", evidence="\n".join(stamped[:10]) or None)
    sess = root / ".deckhand" / "tryon" / "sessions"
    open_ = [p.stem for p in sess.glob("*.json") if '"state": "open"' in p.read_text(encoding="utf-8")] if sess.exists() else []
    staged = list(root.glob("**/dh-tryon/*"))
    row("tryon-closed", not open_ and not [s for s in staged if "node_modules" not in s.parts],
        "no open try-on session" if not open_ else f"open sessions: {', '.join(open_)} (keep or discard)")
    leaked = []
    tracked_env = []
    for p in git_files(root):
        rel = str(p.relative_to(root)).replace("\\", "/")
        if re.search(r"(^|/)\.env($|\.local$|\.production$)", rel):
            tracked_env.append(rel)
        if not p.is_file() or not is_text(p) or rel.startswith(".deckhand/"):
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if SECRET_RX.search(line):
                    leaked.append(f"{rel}:{i}")
        except Exception:
            pass
    gi = (root / ".gitignore").read_text(encoding="utf-8") if (root / ".gitignore").exists() else ""
    env_committed = [e for e in tracked_env if run(["git", "ls-files", "--error-unmatch", e], cwd=root)["code"] == 0]
    row("secrets", not leaked and not env_committed,
        "no credential-shaped value in the repo" if not leaked and not env_committed else f"{len(leaked)} secret-shaped values, {len(env_committed)} committed .env files",
        evidence="\n".join(leaked[:10] + env_committed) or None)
    if ".env" not in gi:
        row("env-ignored", False, ".env is not in .gitignore", blocking=True)
    b = BRAND.check(root, allow=allow)
    row("honesty", b["ok"], f"{b['blocking']} blocking findings, {b['warnings']} warnings (template names, demo content, fake logos, placeholders)",
        evidence="\n".join(f"{f['severity']} {f['file']}:{f['line']} {f['kind']}: {f['text']}" for f in b["findings"][:15]) or None)
    base = url or (read_json(root / ".deckhand" / "dev.json", {}) or {}).get("url")
    if base and "routes" not in skip:
        base = base.rstrip("/")
        sm = read_json(root / ".deckhand" / "sitemap.json", {}) or {}
        routes = {p["route"] for p in sm.get("pages", []) if "[" not in p.get("route", "[") and (p.get("auth") or "public") == "public"}
        st, html = _get(base + "/")
        parser = _Links()
        try:
            parser.feed(html)
        except Exception:
            pass
        routes |= parser.links | {"/"}
        bad = []
        for r_ in sorted(routes)[:80]:
            code, _ = _get(base + r_)
            if not code or code >= 400:
                bad.append(f"{r_} -> {code}")
        row("routes", not bad, f"{len(routes)} routes answer" if not bad else f"{len(bad)} of {len(routes)} routes fail", evidence="\n".join(bad[:20]) or None)
    else:
        row("routes", False, "not checked: no running URL (dh dev start, or --url)", blocking=False)
    a11y = []
    for p in git_files(root):
        if p.suffix in (".tsx", ".jsx") and "node_modules" not in p.parts:
            t = p.read_text(encoding="utf-8", errors="ignore")
            for m in re.finditer(r"<(img|Image)\b(?![^>]*\balt=)[^>]*>", t):
                a11y.append(f"{p.relative_to(root)}: <{m.group(1)}> without alt")
    layout = next((p for p in (root / "app" / "layout.tsx", root / "src" / "app" / "layout.tsx") if p.exists()), None)
    if layout and not re.search(r"<html[^>]*\blang=", layout.read_text(encoding="utf-8")):
        a11y.append(f"{layout.relative_to(root)}: <html> without lang")
    row("a11y-basics", not a11y, "alt text + html lang present" if not a11y else f"{len(a11y)} issues", blocking=False, evidence="\n".join(a11y[:10]) or None)
    if "audit" not in skip and (root / "package-lock.json").exists():
        r = run(["npm", "audit", "--audit-level=high", "--json"], cwd=root, timeout=300)
        m = re.search(r'"high"\s*:\s*(\d+).*?"critical"\s*:\s*(\d+)', r["out"], re.S)
        hi = (int(m.group(1)) + int(m.group(2))) if m else 0
        row("deps-audit", hi == 0, f"{hi} high/critical advisories" if hi else "no high/critical advisories", blocking=False)
    ok = all(r["ok"] for r in rows if r["blocking"])
    report = {"ok": ok, "at": now(), "rows": rows}
    write_json(root / ".deckhand" / "verify.json", report)
    md = ["# Verify report", "", f"{'PASS' if ok else 'FAIL'} — {now()}", "", "| check | result | detail |", "|---|---|---|"]
    for r in rows:
        md.append(f"| {r['check']} | {'ok' if r['ok'] else ('FAIL' if r['blocking'] else 'warn')} | {r['detail']} |")
    (root / ".deckhand" / "VERIFY.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    return report
