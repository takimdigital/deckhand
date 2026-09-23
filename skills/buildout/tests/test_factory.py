"""Template Factory tests — registry scoring, swap gate, clone gate.

Everything here runs offline: registry fixtures are local JSON, the clone test
uses a local `file://` git repo, and no network is touched.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
sys.path.insert(0, str(SCRIPTS))

import swap_check  # noqa: E402


def run(script: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / script), *[str(a) for a in args]],
                          capture_output=True, text=True, cwd=str(cwd) if cwd else None)


# ---------------------------------------------------------------- fixtures
MEASURED_ROWS = {
    "templates": [
        {
            "name": "alpha", "url": "https://github.com/acme/alpha", "repo": "acme/alpha", "rank": 1,
            "status": "verified", "license_spdx": "MIT", "license_ok": 1, "stars": 4200, "pushed_at": "2026-09-01",
            "shape": "saas", "shape_source": "heuristic",
            "stack": {"framework": "next", "db": "postgres", "orm": "drizzle", "auth": "better-auth",
                      "ui": ["tailwind", "shadcn"], "i18n": "next-intl", "rtl": True, "locales": ["fr", "ar"],
                      "jobs": [], "tests": ["vitest"], "docker": True, "admin": True, "package_manager": "pnpm",
                      "lang": "typescript"},
            "deps_vendor": ["stripe"], "deps_selfhost": ["postgres", "docker"],
            "swap_map": {"stripe": {"vendor": "stripe", "target": "keep", "status": "keep", "patterns": ["stripe"],
                                    "target_patterns": ["stripe"], "verified": False}},
            "boot_install_ok": 1, "boot_build_ok": 1, "boot_start_ok": 1, "boot_tests": "pass", "boot_ms": 210000,
            "risk_flags": [], "rebrand_surface": ["src/app/layout.tsx", "public/logo.svg"],
        },
        {
            "name": "beta", "url": "https://github.com/acme/beta", "repo": "acme/beta", "rank": 2,
            "status": "verified", "license_spdx": "Apache-2.0", "license_ok": 1, "stars": 900, "pushed_at": "2026-08-01",
            "shape": "saas",
            "stack": {"framework": "remix", "db": "postgres", "orm": "prisma", "auth": "next-auth",
                      "i18n": None, "rtl": False, "docker": True, "tests": [], "package_manager": "npm"},
            "deps_vendor": ["stripe", "neon", "resend"], "deps_selfhost": ["postgres"],
            "swap_map": {},
            "boot_install_ok": 1, "boot_build_ok": 0, "boot_start_ok": 0,
            "risk_flags": [{"kind": "no-tests", "detail": "no test runner detected"}],
        },
        {
            "name": "gamma", "url": "https://github.com/acme/gamma", "repo": "acme/gamma", "rank": 3,
            "status": "unverified", "license_spdx": None, "license_ok": 0, "stars": 120, "pushed_at": "2024-01-01",
            "shape": "unknown", "stack": {"framework": "next", "db": "unknown", "auth": "clerk"},
            "risk_flags": [{"kind": "license", "detail": "no MIT/Apache-2.0 license found"},
                           {"kind": "stale", "detail": "last push 900 days ago"}],
        },
    ]
}


@pytest.fixture()
def registry(tmp_path: Path) -> tuple[Path, Path]:
    db = tmp_path / "templates.db"
    seed = tmp_path / "seed.json"
    seed.write_text(json.dumps({"templates": [
        {"name": "alpha", "url": "https://github.com/acme/alpha", "rank": 1},
        {"name": "beta", "url": "https://github.com/acme/beta", "rank": 2},
        {"name": "gamma", "url": "https://github.com/acme/gamma", "rank": 3},
    ]}), encoding="utf-8")
    r = run("templates_db.py", "--db", db, "init", "--seed", seed, "--force")
    assert r.returncode == 0, r.stderr
    rows = tmp_path / "rows.json"
    rows.write_text(json.dumps(MEASURED_ROWS), encoding="utf-8")
    r = run("templates_db.py", "--db", db, "import", rows)
    assert r.returncode == 0, r.stderr
    return db, tmp_path


INTAKE = {
    "shape": "saas", "features": ["accounts", "payments", "i18n"],
    "languages": ["fr", "ar"], "hosting": "vps-coolify", "niche": "field service SaaS",
}


# ---------------------------------------------------------------- registry
def test_import_keeps_seed_rank_and_measures(registry):
    db, tmp = registry
    r = run("templates_db.py", "--db", db, "list", "--json")
    assert r.returncode == 0
    rows = {x["name"]: x for x in json.loads(r.stdout)}
    assert rows["alpha"]["rank"] == 1 and rows["alpha"]["license_ok"] == 1
    assert rows["gamma"]["license_ok"] == 0
    assert rows["alpha"]["canonical"] == 1
    assert rows["beta"]["canonical"] == 0  # remix = non-canonical
    assert "framework=remix" in (rows["beta"]["canonical_notes"] or "")


def test_score_prefers_canonical_booting_template(registry):
    db, tmp = registry
    intake = tmp / "intake.json"
    intake.write_text(json.dumps(INTAKE), encoding="utf-8")
    r = run("templates_db.py", "--db", db, "score", "--intake", intake, "--top", "3", "--json")
    assert r.returncode == 0, r.stderr
    payload = json.loads(r.stdout)
    ranked = payload["ranked"]
    blocked = {x["name"]: x for x in payload["blocked"]}
    # beta fails boot on record, gamma has no license -> only alpha may be ranked
    assert [x["name"] for x in ranked] == ["alpha"]
    assert "beta" in blocked and "gamma" in blocked
    assert "build failed" in " ".join(blocked["beta"]["blockers"])
    reasons = " | ".join(ranked[0]["reasons"])
    assert "shape match" in reasons and "RTL" in reasons and "canonical" in reasons and "boots measured green" in reasons


def test_score_is_deterministic(registry):
    db, tmp = registry
    intake = tmp / "intake.json"
    intake.write_text(json.dumps(INTAKE), encoding="utf-8")
    a = run("templates_db.py", "--db", db, "score", "--intake", intake, "--json").stdout
    b = run("templates_db.py", "--db", db, "score", "--intake", intake, "--json").stdout
    assert a == b


def test_export_is_agent_readable(registry):
    db, tmp = registry
    out = tmp / "export.json"
    r = run("templates_db.py", "--db", db, "export", "--out", out)
    assert r.returncode == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["count"] == 3 and isinstance(data["templates"][0]["stack"], dict)


def test_license_gate_blocks_unlicensed(registry):
    """gamma has no license -> score -1 with a blocker, never silently ranked."""
    db, tmp = registry
    intake = tmp / "intake.json"
    intake.write_text(json.dumps(INTAKE), encoding="utf-8")
    out = run("templates_db.py", "--db", db, "score", "--intake", intake, "--json").stdout
    blocked = {x["name"]: x for x in json.loads(out)["ranked"]}  # top3 only
    assert "gamma" not in blocked


# ---------------------------------------------------------------- swap gate
def _project(tmp: Path, name: str, pkg: dict, files: dict[str, str]) -> Path:
    root = tmp / name
    (root / "src").mkdir(parents=True)
    (root / "package.json").write_text(json.dumps({"name": name, "dependencies": pkg}), encoding="utf-8")
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


def _map(tmp: Path, allow: list[str] | None = None) -> Path:
    m = tmp / "swap-map.json"
    m.write_text(json.dumps({"swaps": [{
        "vendor": "clerk", "target": "better-auth", "patterns": ["@clerk/", "clerkMiddleware"],
        "target_patterns": ["better-auth"], "status": "pending", "allow": allow or [], "verified": False,
    }]}), encoding="utf-8")
    return m


def test_swap_check_fails_while_vendor_dep_remains(tmp_path):
    root = _project(tmp_path, "bad", {"@clerk/nextjs": "^5"}, {"src/mw.ts": "import { clerkMiddleware } from '@clerk/nextjs/server'"})
    r = run("swap_check.py", "--project", root, "--map", _map(tmp_path))
    assert r.returncode == 1
    assert "INCOMPLETE" in r.stdout and "@clerk/" in r.stdout


def test_swap_check_passes_when_adapter_present_and_vendor_gone(tmp_path):
    root = _project(tmp_path, "good", {"better-auth": "^1.3"}, {"src/auth.ts": "import { betterAuth } from 'better-auth'"})
    r = run("swap_check.py", "--project", root, "--map", _map(tmp_path))
    assert r.returncode == 0, r.stdout
    assert "OK" in r.stdout


def test_swap_check_allowlist_permits_documented_reference(tmp_path):
    root = _project(tmp_path, "mixed", {"better-auth": "^1.3"},
                    {"src/auth.ts": "export const auth = 1", "docs/migration.md": "was: @clerk/nextjs clerkMiddleware"})
    r = run("swap_check.py", "--project", root, "--map", _map(tmp_path, allow=["docs/*"]))
    assert r.returncode == 0, r.stdout


def test_swap_check_missing_map_is_an_error(tmp_path):
    root = _project(tmp_path, "p", {}, {})
    r = run("swap_check.py", "--project", root)
    assert r.returncode == 2


def test_swap_check_accepts_dict_shaped_map(tmp_path):
    """The registry stores {vendor: entry}; a cloned .factory/swap-map.json must work either way."""
    root = _project(tmp_path, "dictmap", {"@clerk/nextjs": "^5"}, {"src/a.ts": "clerkMiddleware()"})
    m = tmp_path / "swap-map.json"
    m.write_text(json.dumps({"swaps": {"clerk": {
        "vendor": "clerk", "target": "better-auth", "patterns": ["@clerk/", "clerkMiddleware"],
        "target_patterns": ["better-auth"], "status": "pending", "allow": []}}}), encoding="utf-8")
    r = run("swap_check.py", "--project", root, "--map", m)
    assert r.returncode == 1
    assert "INCOMPLETE" in r.stdout and "clerk" in r.stdout


def test_run_resolves_windows_cmd_shims():
    """npm/pnpm are .cmd shims on Windows; _run must resolve them (regression: WinError 2)."""
    import shutil as _sh
    if not _sh.which("npm"):
        pytest.skip("npm not on PATH")
    import _tpl_lib as L
    rc, out, err = L._run(["npm", "--version"], timeout=180)
    assert rc == 0 and out.strip(), f"npm --version failed: rc={rc} err={err[:200]}"


def test_install_runs_in_the_project_dir(tmp_path):
    """Regression: npm install must run with cwd = the cloned project, never the skill dir."""
    import shutil as _sh
    if not _sh.which("npm"):
        pytest.skip("npm not on PATH")
    up = tmp_path / "up"
    (up / "src").mkdir(parents=True)
    (up / "package.json").write_text(json.dumps({
        "name": "fixture", "version": "1.0.0", "private": True,
        "scripts": {"postinstall": "node write-marker.js"}}), encoding="utf-8")
    (up / "write-marker.js").write_text("require('fs').writeFileSync('install-ran.txt','1')\n", encoding="utf-8")
    (up / "LICENSE").write_text("MIT\n", encoding="utf-8")
    for cmd in (["init", "-q"], ["add", "-A"],
                ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"]):
        subprocess.run(["git", *cmd], cwd=up, check=True, capture_output=True)
    root = tmp_path / "projects"
    r = run("factory_clone.py", "--repo", str(up).replace("\\", "/"), "--slug", "inst",
            "--root", root, "--install")
    assert r.returncode == 0, r.stderr
    assert (root / "inst" / "install-ran.txt").is_file(), "npm install did not run in the project dir"
    assert not (Path.cwd() / "install-ran.txt").exists(), "npm install leaked into the caller's cwd"


def test_clone_gitignores_env_when_the_template_does_not(tmp_path):
    """The factory seeds .env; if the template doesn't ignore it, the factory must, before commit."""
    up = tmp_path / "upenv"
    (up / "src").mkdir(parents=True)
    (up / "package.json").write_text(json.dumps({"name": "f", "private": True}), encoding="utf-8")
    (up / ".env.example").write_text("SECRET=\n", encoding="utf-8")
    (up / ".gitignore").write_text("node_modules\n", encoding="utf-8")
    (up / "LICENSE").write_text("MIT\n", encoding="utf-8")
    for cmd in (["init", "-q"], ["add", "-A"],
                ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"]):
        subprocess.run(["git", *cmd], cwd=up, check=True, capture_output=True)
    root = tmp_path / "projects"
    r = run("factory_clone.py", "--repo", str(up).replace("\\", "/"), "--slug", "env", "--root", root)
    assert r.returncode == 0, r.stderr
    assert ".env" in (root / "env" / ".gitignore").read_text(encoding="utf-8")
    tracked = subprocess.run(["git", "ls-files"], cwd=root / "env", capture_output=True, text=True).stdout.split()
    assert ".env" not in tracked


def test_module_level_helpers_are_importable(tmp_path):
    root = _project(tmp_path, "x", {"@clerk/nextjs": "^5"}, {"src/a.ts": "clerkMiddleware()"})
    absent = swap_check.grep_present(root, ["@clerk/"], [])
    assert absent["hits"] and not absent["allowed"]
    present = swap_check.must_present(root, ["@clerk/"])
    assert present["in_package_json"] == ["@clerk/"]
    assert "node_modules" in swap_check.SKIP_DIRS


# ---------------------------------------------------------------- clone gate
def _upstream(tmp_path: Path) -> Path:
    up = tmp_path / "upstream"
    (up / "src").mkdir(parents=True)
    (up / "package.json").write_text(json.dumps({"name": "fixture", "scripts": {"build": "echo ok"}}), encoding="utf-8")
    (up / "LICENSE").write_text("MIT License\n\nCopyright (c) fixture\n", encoding="utf-8")
    (up / "README.md").write_text("# fixture\n", encoding="utf-8")
    for cmd in (["init", "-q"], ["add", "-A"],
                ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"]):
        subprocess.run(["git", *cmd], cwd=up, check=True, capture_output=True)
    return up


def test_factory_clone_writes_state_and_fresh_history(tmp_path):
    up = _upstream(tmp_path)
    root = tmp_path / "projects"
    # native path (not a file:// URI): file:// cloning fails on some Windows git builds
    r = run("factory_clone.py", "--repo", str(up).replace("\\", "/"), "--slug", "pilot", "--root", root, "--json")
    assert r.returncode == 0, r.stderr
    dest = root / "pilot"
    assert (dest / ".factory" / "match.json").exists()
    assert (dest / ".factory" / "swap-map.json").exists()
    assert (dest / ".factory" / "scorecard.md").exists()
    assert (dest / "PENDING.md").read_text(encoding="utf-8").startswith("# PENDING")
    assert not (dest / ".git" / "refs" / "remotes").exists() or not list((dest / ".git").glob("**/remotes"))
    log = subprocess.run(["git", "log", "--oneline"], cwd=dest, capture_output=True, text=True).stdout.strip()
    assert len(log.splitlines()) == 1 and "clone" in log


def test_factory_clone_refuses_unlicensed_registry_row(registry):
    db, tmp = registry
    root = tmp / "projects"
    r = run("factory_clone.py", "--template", "gamma", "--slug", "nope", "--root", root, "--db", db)
    assert r.returncode == 4
    assert "REFUSED" in r.stderr
    assert not (root / "nope").exists()


def test_factory_clone_refuses_existing_nonempty_dir(tmp_path):
    up = _upstream(tmp_path)
    root = tmp_path / "projects"
    (root / "taken").mkdir(parents=True)
    (root / "taken" / "keep.txt").write_text("x", encoding="utf-8")
    r = run("factory_clone.py", "--repo", up.as_uri(), "--slug", "taken", "--root", root)
    assert r.returncode == 5
    assert (root / "taken" / "keep.txt").exists()


# ---------------------------------------------------------------- scoring units
def test_vendor_keys_build_failure_is_not_a_pool_rejection():
    """A build blocked on vendor credentials is a swap input, not a broken template."""
    import templates_db as TDB
    base = {"status": "verified", "license_ok": 1, "archived": 0, "shape": "saas", "stars": 5000,
            "stack": {"framework": "next", "db": "postgres", "auth": "clerk", "docker": True},
            "canonical": 0, "deps_vendor": ["clerk"], "boot_build_ok": 0, "boot_start_ok": 0,
            "risk_flags": [{"kind": "vendor-keys-required", "detail": "build needs clerk"}]}
    intake = {"shape": "saas", "features": [], "languages": ["en"]}
    score, reasons, blockers = TDB.score_template(intake, dict(base, name="v", url="u"))
    assert not blockers, blockers
    assert any("vendor keys" in r for r in reasons)
    # without the flag, the same row is blocked
    no_flag = dict(base, risk_flags=[], name="v2", url="u")
    _, _, blockers2 = TDB.score_template(intake, no_flag)
    assert any("build failed" in b for b in blockers2)


def test_star_tiers_reward_proven_and_penalise_unproven():
    import templates_db as TDB
    base = {"status": "verified", "license_ok": 1, "archived": 0, "shape": "saas",
            "stack": {"framework": "next", "db": "postgres", "auth": "none", "docker": True},
            "canonical": 1, "deps_vendor": [], "risk_flags": [], "boot_start_ok": 1}
    intake = {"shape": "saas", "features": [], "languages": ["en"]}
    hot, hot_reasons, _ = TDB.score_template(intake, dict(base, name="hot", url="u", stars=5000))
    mid, _, _ = TDB.score_template(intake, dict(base, name="mid", url="u", stars=900))
    cold, cold_reasons, _ = TDB.score_template(intake, dict(base, name="cold", url="u", stars=2))
    assert hot > mid > cold
    assert hot - cold >= 15
    assert any("community" in r for r in hot_reasons)
    assert any("unproven" in r for r in cold_reasons)


# ------------------------------------------------- audit regressions (2026-09-23)
def test_swap_check_ignores_its_own_map_in_the_project(tmp_path):
    """Regression: the map lives in .factory/ and quotes the vendor patterns — counting it as
    leftover vendor code made exit 0 structurally unreachable for every real project."""
    root = _project(tmp_path, "selfmap", {"better-auth": "^1.3"},
                    {"src/auth.ts": "import { betterAuth } from 'better-auth'"})
    fdir = root / ".factory"
    fdir.mkdir()
    (fdir / "swap-map.json").write_text(json.dumps({"swaps": [{
        "vendor": "clerk", "target": "better-auth", "patterns": ["@clerk/", "clerkMiddleware"],
        "target_patterns": ["better-auth"], "status": "pending", "allow": []}]}), encoding="utf-8")
    r = run("swap_check.py", "--project", root)   # no --map: uses .factory/swap-map.json
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK" in r.stdout


def test_swap_check_empty_map_is_not_a_pass(tmp_path):
    """Regression: an empty map (e.g. a --repo clone) used to print a note and exit 0."""
    root = _project(tmp_path, "emptymap", {}, {})
    fdir = root / ".factory"
    fdir.mkdir()
    (fdir / "swap-map.json").write_text(json.dumps({"swaps": []}), encoding="utf-8")
    r = run("swap_check.py", "--project", root)
    assert r.returncode == 3
    assert "NOTHING-TO-VERIFY" in r.stdout


def test_swap_check_removal_mode_proves_absence_only(tmp_path):
    """`glitchtip or none` style targets: the vendor must be gone; no phantom library is required."""
    root = _project(tmp_path, "owncode", {}, {"src/mw.ts": "export function middleware() {}"})
    m = tmp_path / "swap-map.json"
    m.write_text(json.dumps({"swaps": [{
        "vendor": "sentry", "target": "glitchtip or none", "patterns": ["@sentry/"],
        "target_patterns": ["glitchtip"], "status": "removed", "allow": []}]}), encoding="utf-8")
    r = run("swap_check.py", "--project", root, "--map", m)
    assert r.returncode == 0, r.stdout
    assert "REMOVED" in r.stdout
    (root / "src" / "sentry.ts").write_text("import * as Sentry from '@sentry/nextjs'", encoding="utf-8")
    r2 = run("swap_check.py", "--project", root, "--map", m)
    assert r2.returncode == 1 and "INCOMPLETE" in r2.stdout


def test_vendor_target_patterns_are_identifiers_not_prose():
    """The gate greps for the target: prose can never satisfy it, so the map must carry real needles."""
    import _tpl_lib as L
    _v, _s, _u, swap_map = L.classify_deps(["ably", "launchdarkly", "sentry"], "")
    assert swap_map["ably"]["target_patterns"] == ["socket.io", "eventsource", "text/event-stream"]
    assert "socket.io-or-sse" not in " ".join(swap_map["ably"]["target_patterns"])
    assert swap_map["launchdarkly"]["status"] == "own-code"   # own code: absence-only
    assert swap_map["sentry"]["removal_ok"] is True
    for vendor, e in swap_map.items():
        if e["status"] not in ("keep", "own-code", "removed") and not e.get("removal_ok"):
            assert e["target_patterns"], f"{vendor} has no identifiers and is not removal-ok"


def test_clone_refuses_a_repo_path_without_a_license(tmp_path):
    """Regression: `--repo <path>` used to bypass the licence gate entirely (cloned with exit 0)."""
    up = tmp_path / "nol"
    (up / "src").mkdir(parents=True)
    (up / "package.json").write_text(json.dumps({"name": "f", "private": True}), encoding="utf-8")
    for cmd in (["init", "-q"], ["add", "-A"],
                ["-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"]):
        subprocess.run(["git", *cmd], cwd=up, check=True, capture_output=True)
    r = run("factory_clone.py", "--repo", str(up).replace("\\", "/"), "--slug", "nolic",
            "--root", tmp_path / "projects")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "REFUSED" in r.stderr
    assert not (tmp_path / "projects" / "nolic").exists()


def test_clone_pins_a_commit_sha(tmp_path):
    """`--ref <sha>`: git clone --branch only takes names — a sha must be fetched and checked out.

    The project's own history is fresh (HEAD is not the upstream commit, by design), so the pin is
    proved where it is recorded: `.factory/match.json`'s upstream_commit.
    """
    up = _upstream(tmp_path)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=up, capture_output=True, text=True).stdout.strip()
    root = tmp_path / "projects"
    r = run("factory_clone.py", "--repo", str(up).replace("\\", "/"), "--slug", "pinned",
            "--root", root, "--ref", sha)
    assert r.returncode == 0, r.stderr
    match = json.loads((root / "pinned" / ".factory" / "match.json").read_text(encoding="utf-8"))
    assert match["upstream_commit"] == sha
    assert match["ref"] == sha


def test_adapter_must_be_code_or_a_dependency(tmp_path):
    """Regression: `.oxlintrc.json` lists the `EventSource` global — that is not an adapter."""
    root = _project(tmp_path, "lintcfg", {}, {".oxlintrc.json": '{"globals": {"EventSource": "readonly"}}',
                                              "README.md": "we use eventsource in the browser"})
    m = tmp_path / "swap-map.json"
    m.write_text(json.dumps({"swaps": [{
        "vendor": "ably", "target": "socket.io-or-sse", "patterns": ["ably"],
        "target_patterns": ["socket.io", "eventsource"], "status": "pending", "allow": []}]}), encoding="utf-8")
    r = run("swap_check.py", "--project", root, "--map", m)
    assert r.returncode == 1, r.stdout          # no adapter in code, no dependency → not proof
    # the moment real code (or the dependency) carries it, the entry passes
    (root / "src" / "rt.ts").write_text("import { EventSourcePolyfill } from 'eventsource'\n", encoding="utf-8")
    r2 = run("swap_check.py", "--project", root, "--map", m)
    assert r2.returncode == 0, r2.stdout


def test_vendor_needles_do_not_match_inside_words(tmp_path):
    """Regression: 'ably' matched 'pro-bably' in a README — a ghost that costs a real hunt."""
    root = _project(tmp_path, "words", {"better-auth": "^1.3"},
                    {"README.md": "It is probably overkill for small projects.",
                     "src/a.ts": "import { betterAuth } from 'better-auth'"})
    m = tmp_path / "swap-map.json"
    m.write_text(json.dumps({"swaps": [{
        "vendor": "ably", "target": "socket.io-or-sse", "patterns": ["ably"],
        "target_patterns": ["socket.io", "eventsource"], "status": "removed", "allow": []}]}), encoding="utf-8")
    r = run("swap_check.py", "--project", root, "--map", m)
    assert r.returncode == 0, r.stdout          # "probably" is not a vendor reference
    # but a real reference is still caught, and a symbol pattern stays substring-based
    (root / "src" / "rt.ts").write_text("import Ably from 'ably'", encoding="utf-8")
    r2 = run("swap_check.py", "--project", root, "--map", m)
    assert r2.returncode == 1 and "INCOMPLETE" in r2.stdout


def test_clone_scans_the_clone_for_vendors(tmp_path):
    """The map must describe the CLONE: a --repo clone starts empty, the local scan fills it."""
    up = _upstream(tmp_path)
    (up / "package.json").write_text(json.dumps({"name": "u", "dependencies": {"@clerk/nextjs": "^5"}}),
                                    encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=up, check=True, capture_output=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "deps"],
                   cwd=up, check=True, capture_output=True)
    root = tmp_path / "projects"
    r = run("factory_clone.py", "--repo", str(up).replace("\\", "/"), "--slug", "scanned", "--root", root)
    assert r.returncode == 0, r.stderr
    m = json.loads((root / "scanned" / ".factory" / "swap-map.json").read_text(encoding="utf-8"))
    vendors = {e["vendor"] for e in m["swaps"]}
    assert "clerk" in vendors, m
    assert any(e.get("source") == "local-scan" for e in m["swaps"])
    # and the commit was cut before any install artifact could land in it
    log = subprocess.run(["git", "log", "--oneline"], cwd=root / "scanned",
                         capture_output=True, text=True).stdout.strip()
    assert len(log.splitlines()) == 1
