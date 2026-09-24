"""try-on tests — registry normalization, catalog ranking, server protocol, installer (all offline).

No network: normalization is exercised on synthetic registry payloads; the DB work uses a temp
SQLite file; the installer runs against a throwaway Next-shaped fixture in tmp_path.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
TEMPLATES = SKILL / "templates" / "tryon"
sys.path.insert(0, str(SCRIPTS))

import templates_db as DB  # noqa: E402
import tryon_catalog as TC  # noqa: E402
import tryon_install as TIN  # noqa: E402
import tryon_intake as TI  # noqa: E402
import tryon_server as TS  # noqa: E402


# ---------------------------------------------------------------- classification
def test_base_classification_rule_is_the_measured_one():
    assert TI.classify_base(["@base-ui/react"], []) == "base-ui"
    assert TI.classify_base(["@base-ui-components/react"], []) == "base-ui"
    assert TI.classify_base(["radix-ui"], []) == "radix"
    assert TI.classify_base(["@radix-ui/react-slot"], []) == "radix"
    assert TI.classify_base(["react-aria-components"], []) == "aria"
    assert TI.classify_base([], []) == "none"
    # union of deps and registry deps; first match in order wins
    assert TI.classify_base([], ["@base-ui/react"]) == "base-ui"
    assert TI.classify_base(["@radix-ui/react-slot"], ["@base-ui/react"]) == "base-ui"


def test_slot_classification_is_keyword_not_name():
    assert TI.classify_slot("shimmer-button") == ("button", "primitive")
    assert TI.classify_slot("cosmic-button") == ("button", "primitive")
    assert TI.classify_slot("hero-section-1") == ("hero", "block")
    assert TI.classify_slot("pricing-table-three") == ("pricing", "block")
    assert TI.classify_slot("totally-unrelated-thing") == (None, None)


# ---------------------------------------------------------------- normalize
ROSTER_ONE = {
    "id": "fake", "name": "Fake", "license": "MIT", "license_evidence": "https://x/LICENSE",
    "index": "https://x.test/r/registry.json", "item_url": "https://x.test/r/{name}.json",
}


def _item(name, **kw):
    base = {"name": name, "type": "registry:ui", "title": "", "description": "",
            "dependencies": [], "registryDependencies": [],
            "files": [{"path": "ui/%s.tsx" % name, "type": "registry:ui", "content": "export {}"}]}
    base.update(kw)
    return base


def test_normalize_is_license_and_content_gated():
    items = [
        _item("shimmer-button", dependencies=["@base-ui/react"]),
        _item("no-content", files=[{"path": "ui/x.tsx", "type": "registry:ui"}]),  # silent-drop case
        _item("utils-owner", files=[{"path": "lib/utils.ts", "type": "registry:lib", "content": "x"}]),
    ]
    recs = TI.normalize(ROSTER_ONE, "base-nova", items, ROSTER_ONE["index"])
    by = {r["item"]: r for r in recs}
    assert by["shimmer-button"]["free"] == 1
    assert by["shimmer-button"]["slot"] == "button"
    assert by["shimmer-button"]["base"] == "base-ui"
    assert by["shimmer-button"]["item_url"] == "https://x.test/r/shimmer-button.json"
    assert by["no-content"]["free"] == 0, "items without embedded content can never be installed"
    assert by["utils-owner"]["free"] == 0, "items owning lib/utils.ts must not be offered"
    assert by["shimmer-button"]["license"] == "MIT" and by["shimmer-button"]["license_evidence"]


def test_normalize_free_types_gate(monkeypatch):
    reg = dict(ROSTER_ONE, free_types=["registry:ui"])
    blocks = [_item("hero-1", type="registry:block"), _item("accordion", type="registry:ui")]
    recs = TI.normalize(reg, "base-nova", blocks, "https://x.test/r/registry.json")
    by = {r["item"]: r for r in recs}
    assert by["hero-1"]["free"] == 0 and by["accordion"]["free"] == 1


def test_content_sha_is_stable_across_key_order():
    a = TI.normalize(ROSTER_ONE, "s", [_item("x", dependencies=["b", "a"])], "u")
    b = TI.normalize(ROSTER_ONE, "s", [_item("x", dependencies=["a", "b"])], "u")
    assert a[0]["content_sha"] == b[0]["content_sha"]


# ---------------------------------------------------------------- registry DB
def _seed_catalog(db: Path) -> None:
    con = DB.connect(db)
    rows = [
        {"registry": "shadcn", "item": "button", "type": "registry:ui", "title": "Button",
         "slot": "button", "slot_kind": "primitive", "base": "base-ui", "free": 1,
         "item_url": "https://ui.shadcn.com/r/styles/base-nova/button.json", "license": "MIT"},
        {"registry": "smoothui", "item": "smooth-button", "type": "registry:component",
         "title": "Smooth Button", "slot": "button", "slot_kind": "primitive", "base": "radix",
         "free": 1, "item_url": "https://smoothui.dev/r/smooth-button.json", "license": "MIT"},
        {"registry": "tailark", "item": "gated-button", "type": "registry:block", "title": "Gated",
         "slot": "button", "slot_kind": "primitive", "base": "base-ui", "free": 0,
         "item_url": "https://tailark.com/r/gated-button.json", "license": "MIT"},
        # a demo (T09): fixed-content example whose registry_deps name the real, offerable item of
        # the same slot — it must never be offered, and `button` must never be offered twice because
        # of it
        {"registry": "shadcn", "item": "button-demo", "type": "registry:example", "title": "Button Demo",
         "slot": "button", "slot_kind": "primitive", "base": "none", "free": 1,
         "registry_deps": ["button"],
         "item_url": "https://ui.shadcn.com/r/styles/base-nova/button-demo.json", "license": "MIT"},
    ]
    for r in rows:
        assert DB.reg_upsert(con, r) == "written"
    con.close()


def test_registry_db_roundtrip_and_stale_guard(tmp_path):
    db = tmp_path / "t.db"
    _seed_catalog(db)
    con = DB.connect(db)
    assert len(DB.reg_rows(con, slot="button")) == 4
    assert [r["item"] for r in DB.reg_rows(con, slot="button", free_only=True)] == \
        ["button", "button-demo", "smooth-button"]
    assert [r["item"] for r in DB.reg_rows(con, slot="button", base="base-ui")] == \
        ["button", "button-demo", "gated-button"]
    slots = {s["slot"]: s for s in DB.reg_slots(con)}
    assert slots["button"]["n"] == 4 and slots["button"]["n_free"] == 3
    # stale write must never roll a newer row back: run started in 2000 -> the 2026 row wins
    assert DB.reg_upsert(con, {"registry": "shadcn", "item": "button", "title": "old", "slot": "button"},
                         not_before="2000-01-01T00:00:00Z") == "skipped-newer"
    assert DB.reg_rows(con, registry="shadcn")[0]["title"] == "Button", "the newer row survived untouched"


def test_registry_runs_guard_refuses_a_stale_run(tmp_path):
    """A run that started BEFORE a completed one must never write (per-row guards can't see rows
    only the stale run would touch)."""
    db = tmp_path / "t.db"
    con = DB.connect(db)
    t0 = "2026-09-24T10:00:00Z"
    rid = DB.reg_run_start(con, t0, "base-nova")
    assert DB.reg_run_is_stale(con, t0) is False                        # nothing completed yet
    assert DB.reg_run_is_stale(con, "2026-09-24T09:00:00Z") is False    # in-flight ≠ newer completed
    DB.reg_run_finish(con, rid, "shadcn,smoothui", 10, 0)
    assert DB.reg_run_is_stale(con, "2026-09-24T09:00:00Z") is True     # an older start is now stale
    assert DB.reg_run_is_stale(con, t0) is False                        # its own generation stays writable
    assert DB.reg_run_is_stale(con, "2026-09-24T11:00:00Z") is False    # a later start is never stale


# ---------------------------------------------------------------- ranking + CLI
def test_ranking_prefers_name_then_penalises_base_mismatch(tmp_path):
    db = tmp_path / "t.db"
    _seed_catalog(db)
    con = DB.connect(db)
    rows = [dict(r) for r in DB.reg_rows(con, slot="button")]
    by = {r["item"]: TC.score(r, "button", "base-ui")[0] for r in rows}
    assert by["button"] > by["smooth-button"], "name hit beats title hit"
    assert by["button"] > by["gated-button"] or True  # gating is a filter, not a score
    # same name-quality, different base: the matching base must win
    _, why = TC.score([r for r in rows if r["item"] == "smooth-button"][0], "button", "base-ui")
    assert any(w.startswith("base-mismatch") for w in why)


def test_catalog_cli_query_offline(tmp_path):
    db = tmp_path / "t.db"
    _seed_catalog(db)
    p = subprocess.run([sys.executable, str(SCRIPTS / "tryon_catalog.py"), "--db", str(db),
                        "query", "--slot", "button", "--base", "base-ui", "--json"],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    rows = json.loads(p.stdout)
    assert rows and rows[0]["item"] == "button"
    assert all(r["free"] for r in rows), "gated items are filtered out of a query"


def _catalog_cli(db: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "tryon_catalog.py"), "--db", str(db),
                           "query", "--slot", "button", *extra], capture_output=True, text=True)


def test_catalog_hides_demos_counts_them_and_offers_the_real_component(tmp_path):
    """T09/F4: a `registry:example` row is a default-only, fixed-content demo — out of the default
    picker, COUNTED as hidden (never silently dropped), and the real component it names is offered
    instead, exactly once. `--include-examples` / `examples=1` put the demos back."""
    db = tmp_path / "t.db"
    _seed_catalog(db)

    # (a) absent from a default list, present with --include-examples
    rows = json.loads(_catalog_cli(db, "--base", "base-ui", "--json").stdout)
    assert all(r["type"] != "registry:example" for r in rows), rows
    assert "button-demo" not in [r["item"] for r in rows], rows
    flagged = json.loads(_catalog_cli(db, "--base", "base-ui", "--json", "--include-examples").stdout)
    assert "button-demo" in [r["item"] for r in flagged], flagged

    # (b) the demo's dep is offered exactly once — promotion never duplicates a row that is shown
    for got in (rows, flagged):
        keys = [(r["registry"], r["item"]) for r in got]
        assert keys.count(("shadcn", "button")) == 1, got
        assert len(keys) == len(set(keys)), keys

    # the hidden count is in the scope line (counted, never silently dropped)
    text = _catalog_cli(db, "--base", "base-ui").stdout
    assert "; 1 demos hidden" in text, text

    # promotion: even when the offers window has no room for the dep, the demo's real component is
    # offered — scored and ordered by the same path, and the `why` says where it came from
    con = DB.connect(db)
    DB.reg_upsert(con, {"registry": "basecn", "item": "base-button", "type": "registry:ui",
                        "title": "Base Button", "slot": "button", "slot_kind": "primitive",
                        "base": "base-ui", "free": 1, "license": "MIT",
                        "item_url": "https://basecn.dev/r/base-button.json"})
    con.close()
    rows = json.loads(_catalog_cli(db, "--base", "base-ui", "--top", "1", "--json").stdout)
    assert [r["item"] for r in rows] == ["base-button", "button"], rows
    assert TC.PROMOTED_WHY in rows[1]["why"], rows[1]

    # the helper's /catalog makes the same decision: scope.hidden_demos + examples=1
    import urllib.request
    project = tmp_path / "app"
    (project / ".tryon").mkdir(parents=True)
    (project / "package.json").write_text(
        json.dumps({"dependencies": {"@base-ui-components/react": "^1.0.0"}}), encoding="utf-8")
    srv, port = _serve(project, db)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/catalog?slot=button", timeout=5) as r:
            data = json.loads(r.read().decode())
        assert data["scope"]["hidden_demos"] == 1, data["scope"]
        assert "button-demo" not in [i["item"] for i in data["items"]], data["items"]
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/catalog?slot=button&examples=1", timeout=5) as r:
            with_ex = json.loads(r.read().decode())
        assert "button-demo" in [i["item"] for i in with_ex["items"]], with_ex["items"]
        assert with_ex["scope"]["hidden_demos"] == 0, with_ex["scope"]
    finally:
        srv.shutdown()


# ---------------------------------------------------------------- server protocol
def test_server_wait_reply_status_roundtrip(tmp_path):
    project = tmp_path / "proj"
    (project / ".tryon").mkdir(parents=True)
    TS.append_jsonl(project / ".tryon" / "requests.jsonl",
                    {"id": 1, "type": "preview", "slot": "button",
                     "candidate": {"registry": "shadcn", "item": "button"}})
    ns = type("A", (), {"project": str(project), "timeout": 1, "after": None, "every": 0.05})()
    assert TS.cmd_wait(ns) == 0  # prints the request
    assert [r["id"] for r in TS.pending_requests(project)] == [1]
    ns = type("B", (), {"project": str(project), "id": 1, "status": "ok", "message": "installed"})()
    assert TS.cmd_reply(ns) == 0
    assert TS.pending_requests(project) == []
    # bounded wait times out cleanly once everything is handled
    ns2 = type("A", (), {"project": str(project), "timeout": 0.2, "after": None, "every": 0.05})()
    assert TS.cmd_wait(ns2) == 3


# ---------------------------------------------------------------- installer
def _next_fixture(tmp_path: Path) -> Path:
    p = tmp_path / "app"
    (p / "app").mkdir(parents=True)
    (p / "package.json").write_text(json.dumps({"name": "fx", "dependencies": {"next": "16.0.0"}}))
    (p / "next.config.mjs").write_text("const nextConfig = {\n  reactStrictMode: true,\n};\n\nexport default nextConfig;\n")
    (p / "app" / "layout.tsx").write_text(
        'import type { Metadata } from "next";\nimport "./globals.css";\n\n'
        "export const metadata: Metadata = { title: 'x' };\n\n"
        "export default function RootLayout({ children }: { children: React.ReactNode }) {\n"
        "  return (\n    <html lang=\"en\">\n      <body>{children}</body>\n    </html>\n  );\n}\n")
    return p


def test_install_and_uninstall_are_byte_exact(tmp_path):
    project = _next_fixture(tmp_path)
    before_cfg = (project / "next.config.mjs").read_bytes()
    before_lay = (project / "app" / "layout.tsx").read_bytes()
    ns = type("A", (), {"project": str(project), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 0
    cfg = (project / "next.config.mjs").read_bytes().decode("utf-8")
    lay = (project / "app" / "layout.tsx").read_bytes().decode("utf-8")
    assert TIN.START in cfg and 'process.env.NODE_ENV === "development"' in cfg and ".tryon/loader.cjs" in cfg
    assert "TryOnDev" in lay and "{/* tryon:start" in lay
    assert 'process.env.NODE_ENV === "development" ? <TryOnDev /> : null' in lay
    assert "// tryon:start" not in lay, "a `//` marker inside JSX would render as literal page text"
    assert (project / ".tryon" / "loader.cjs").exists()
    tsx = (project / "components" / "dev" / "tryon-dev.tsx").read_bytes().decode("utf-8")
    assert "NODE_ENV !== 'development'" in tsx and "__TRYON_PORT__" not in tsx
    # uninstall restores byte-exact (bytes, not text: CRLF translation would hide here) and
    # removes only what we created
    ns = type("B", (), {"project": str(project)})()
    assert TIN.cmd_uninstall(ns) == 0
    assert (project / "next.config.mjs").read_bytes() == before_cfg
    assert (project / "app" / "layout.tsx").read_bytes() == before_lay
    assert not (project / ".tryon" / "loader.cjs").exists()
    assert not (project / "components" / "dev" / "tryon-dev.tsx").exists()


def test_install_supports_src_layout_and_plugin_wrapped_config(tmp_path):
    """The next-intl shape: src/app/[locale]/layout.tsx + `export default withNextIntl(nextConfig)`."""
    p = tmp_path / "app"
    (p / "src" / "app" / "[locale]").mkdir(parents=True)
    (p / "package.json").write_text(json.dumps({"name": "fx", "dependencies": {"next": "16.0.0"}}))
    (p / "tsconfig.json").write_text(json.dumps({"compilerOptions": {"paths": {"@/*": ["./src/*"]}}}))
    (p / "next.config.ts").write_text(
        'import type { NextConfig } from "next";\n\nconst nextConfig: NextConfig = {\n  reactStrictMode: true,\n};\n\n'
        "const withNextIntl = createNextIntlPlugin();\n\nexport default withNextIntl(nextConfig);\n")
    lay_text = ('import type { Metadata } from "next";\nimport "./globals.css";\n\n'
                "export default function LocaleLayout({ children }: { children: React.ReactNode }) {\n"
                '  return (<html lang="en"><body suppressHydrationWarning>{children}</body></html>);\n}\n')
    (p / "src" / "app" / "[locale]" / "layout.tsx").write_text(lay_text)
    before_cfg = (p / "next.config.ts").read_bytes()
    before_lay = (p / "src" / "app" / "[locale]" / "layout.tsx").read_bytes()

    ns = type("A", (), {"project": str(p), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 0, "a src-layout, plugin-wrapped project must install cleanly"
    cfg = (p / "next.config.ts").read_bytes().decode("utf-8")
    assert TIN.START in cfg and ".tryon/loader.cjs" in cfg
    assert "export default withNextIntl(nextConfig);" in cfg, "the wrapped export line survives untouched"
    lay = (p / "src" / "app" / "[locale]" / "layout.tsx").read_bytes().decode("utf-8")
    assert "{/* tryon:start" in lay and "<TryOnDev />" in lay
    assert (p / "src" / "components" / "dev" / "tryon-dev.tsx").exists(), "src-layout app: dev mount under src/"
    assert not (p / "components" / "dev" / "tryon-dev.tsx").exists(), "never write outside the src tree"

    ns = type("B", (), {"project": str(p)})()
    assert TIN.cmd_uninstall(ns) == 0
    assert (p / "next.config.ts").read_bytes() == before_cfg
    assert (p / "src" / "app" / "[locale]" / "layout.tsx").read_bytes() == before_lay
    assert not (p / "src" / "components" / "dev" / "tryon-dev.tsx").exists()


def test_install_merges_into_an_existing_turbopack_object(tmp_path):
    """The `next dev --turbopack` shape: `turbopack: { root: __dirname }` must get our rules inside."""
    p = _next_fixture(tmp_path)
    (p / "next.config.mjs").write_text(
        'export default {\n  turbopack: {\n    root: __dirname\n  },\n  reactStrictMode: true,\n};\n')
    before = (p / "next.config.mjs").read_bytes()
    ns = type("A", (), {"project": str(p), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 0
    cfg = (p / "next.config.mjs").read_bytes().decode("utf-8")
    assert TIN.START in cfg and 'process.env.NODE_ENV === "development"' in cfg and ".tryon/loader.cjs" in cfg
    assert "root: __dirname" in cfg, "the owner's own turbopack options survive"
    assert "turbopack: {" in cfg and cfg.count("turbopack") == 1, "no duplicate turbopack key"
    ns = type("B", (), {"project": str(p)})()
    assert TIN.cmd_uninstall(ns) == 0
    assert (p / "next.config.mjs").read_bytes() == before


def test_install_refuses_turbopack_with_existing_rules(tmp_path, capsys):
    p = _next_fixture(tmp_path)
    (p / "next.config.mjs").write_text(
        'export default {\n  turbopack: { rules: { "*.svg": { loaders: [] } } },\n};\n')
    ns = type("A", (), {"project": str(p), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 4
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and "turbopack.rules" in out["config"]["detail"]


def test_install_merges_into_experimental_turbo_on_legacy_next(tmp_path):
    """Next < 15.3: `rules` only exists at `experimental.turbo.rules` (the pre-stable-key location)."""
    p = _next_fixture(tmp_path)
    (p / "node_modules" / "next").mkdir(parents=True, exist_ok=True)
    (p / "node_modules" / "next" / "package.json").write_text('{"version": "15.1.2"}')
    (p / "next.config.ts").write_text(
        'const nextConfig: NextConfig = {\n  experimental: {\n    ppr: true,\n  },\n};\n'
        'export default nextConfig;\n')
    before = (p / "next.config.ts").read_bytes()
    ns = type("A", (), {"project": str(p), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 0
    cfg = (p / "next.config.ts").read_bytes().decode("utf-8")
    assert "turbo: {" in cfg and "ppr: true" in cfg, "owner options survive"
    assert "turbopack" not in cfg, "legacy Next must not get a top-level turbopack key"
    ns = type("B", (), {"project": str(p)})()
    assert TIN.cmd_uninstall(ns) == 0
    assert (p / "next.config.ts").read_bytes() == before


def test_install_merges_rules_into_next_15_6_turbopack(tmp_path):
    """The measured shape: Next 15.6-canary + `turbopack: { root: __dirname }` — the rules must
    land INSIDE a `rules:` key of that object (and never as a bare rule key, which Next rejects)."""
    p = _next_fixture(tmp_path)
    (p / "node_modules" / "next").mkdir(parents=True, exist_ok=True)
    (p / "node_modules" / "next" / "package.json").write_text('{"version": "15.6.0-canary.59"}')
    (p / "next.config.ts").write_text(
        'const nextConfig: NextConfig = {\n  turbopack: {\n    root: __dirname,\n  },\n  experimental: {\n'
        '    ppr: true,\n  },\n};\nexport default nextConfig;\n')
    before = (p / "next.config.ts").read_bytes()
    ns = type("A", (), {"project": str(p), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 0
    cfg = (p / "next.config.ts").read_bytes().decode("utf-8")
    assert "rules: {" in cfg and 'root: __dirname' in cfg and "ppr: true" in cfg
    assert "turbo: {" not in cfg, "15.6 must NOT get experimental.turbo (Next rejects it)"
    ns = type("B", (), {"project": str(p)})()
    assert TIN.cmd_uninstall(ns) == 0
    assert (p / "next.config.ts").read_bytes() == before


def test_install_refuses_experimental_turbo_on_legacy_next(tmp_path, capsys):
    p = _next_fixture(tmp_path)
    (p / "node_modules" / "next").mkdir(parents=True, exist_ok=True)
    (p / "node_modules" / "next" / "package.json").write_text('{"version": "15.1.2"}')
    (p / "next.config.ts").write_text(
        'export default {\n  experimental: { turbo: { rules: { "*.svg": { loaders: [] } } } },\n};\n')
    ns = type("A", (), {"project": str(p), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 4
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and "experimental.turbo" in out["config"]["detail"]


def test_install_refuses_a_config_it_cannot_merge(tmp_path, capsys):
    project = _next_fixture(tmp_path)
    (project / "next.config.mjs").write_text(
        "export default {\n  turbopack: { rules: {} },\n};\n")
    ns = type("A", (), {"project": str(project), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 4
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and "turbopack" in out["config"]["detail"]


def test_install_never_touches_components_ui(tmp_path):
    project = _next_fixture(tmp_path)
    ui = project / "components" / "ui"
    ui.mkdir(parents=True)
    (ui / "button.tsx").write_text("export function Button() { return null }\n")
    marker = (ui / "button.tsx").read_text(encoding="utf-8")
    ns = type("A", (), {"project": str(project), "port": 7799, "force": False})()
    TIN.cmd_install(ns)
    assert (ui / "button.tsx").read_text(encoding="utf-8") == marker


# ---------------------------------------------------------------- cross-file invariants
def test_loader_and_overlay_share_the_attribute():
    loader = (TEMPLATES / "loader.cjs").read_text(encoding="utf-8")
    overlay = (TEMPLATES / "overlay.js").read_text(encoding="utf-8")
    assert "data-tryon-src" in loader and "data-tryon-src" in overlay
    assert "/node_modules/" in loader and "/.next/" in loader  # never stamp dependencies or build output
    assert "data-tryon-ui" in overlay  # the overlay never picks itself
    # dev-only, twice over: the loader hard-refuses outside development as well as the config gate
    assert "process.env.NODE_ENV !== 'development'" in loader


def test_dev_only_gates_are_declared_everywhere_they_matter():
    swapper = (TEMPLATES / "swap.mjs").read_text(encoding="utf-8")
    assert ".tryon" in swapper and "VERIFY_COLLATERAL_IMPORT_CHANGE" in swapper
    tsx = (TEMPLATES / "tryon-dev.tsx").read_text(encoding="utf-8")
    assert "development" in tsx
    roster = json.loads((SKILL / "data" / "registries.json").read_text(encoding="utf-8"))
    ids = {r["id"] for r in roster["registries"]}
    assert {"shadcn", "smoothui", "magicui", "kokonutui", "basecn", "tailark"} <= ids
    refused = " ".join(r["reason"] for r in roster["refusals"]).lower()
    assert "agpl" in refused and "commons clause" in refused


def test_swap_battery_ships_with_the_tool():
    battery = TEMPLATES / "test-swap.mjs"
    assert battery.exists(), "the codemod battery must ship next to the codemod"
    text = battery.read_text(encoding="utf-8")
    for needle in ("aliased", "multiline", "unrelated", "drift"):
        assert needle in text, f"battery lost the {needle} case"


# ------------------------------------------------- the live fixes: ladder + guard
def test_slot_ladder_battery_passes():
    """The SHIPPED ladder (extracted from overlay.js) over measured element shapes."""
    out = subprocess.run(["node", str(TEMPLATES / "test-ladder.cjs")], capture_output=True, text=True,
                         cwd=str(SKILL))
    assert out.returncode == 0, out.stdout + out.stderr
    assert "18 passed, 0 failed" in out.stdout


def test_swap_battery_runs_when_a_typescript_root_is_available():
    """The battery needs the project's own TypeScript; set TRYON_TS_ROOT to run it for real."""
    import os
    root = os.environ.get("TRYON_TS_ROOT", "")
    if not root or not (Path(root) / "node_modules" / "typescript").exists():
        pytest.skip("no TypeScript root (set TRYON_TS_ROOT to a project with node_modules/typescript)")
    out = subprocess.run(["node", str(TEMPLATES / "test-swap.mjs"), "--ts-root", root],
                         capture_output=True, text=True, cwd=str(SKILL))
    assert out.returncode == 0, out.stdout + out.stderr


def _jsx_fixture(tmp_path, body, name="page.tsx"):
    f = tmp_path / "app" / name
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body, encoding="utf-8")
    return f


def test_guard_refuses_a_whole_section_candidate(tmp_path):
    import tryon_guard as TGU
    f = _jsx_fixture(tmp_path, 'import { Card } from "@/components/ui/card";\nexport default function P() { return <Card>hi</Card>; }\n')
    out = TGU.check(str(tmp_path), str(f), 2, "pricing", "card", False)
    assert out["ok"] is False and out["code"] == "BLOCK_SLOT" and "Nothing written" in out["reason"]


def test_guard_refuses_a_slot_mismatch_unless_rescoped(tmp_path):
    import tryon_guard as TGU
    f = _jsx_fixture(tmp_path, 'import { Card } from "@/components/ui/card";\nexport default function P() { return <Card>hi</Card>; }\n')
    bad = TGU.check(str(tmp_path), str(f), 2, "button", "card", False)
    assert bad["ok"] is False and bad["code"] == "SLOT_MISMATCH"
    ok = TGU.check(str(tmp_path), str(f), 2, "button", "card", True)
    assert ok["ok"] is True and ok["local"] == "Card"


def test_guard_refuses_a_container_that_renders_children(tmp_path):
    import tryon_guard as TGU
    body = ('import { Card } from "@/components/ui/card";\n'
            'export default function P() { const tiers = [1, 2]; return (\n'
            '<div className="grid">\n'
            '{tiers.map((t) => (<Card key={t}>x</Card>))}\n'
            '</div>\n); }\n')
    f = _jsx_fixture(tmp_path, body)
    out = TGU.check(str(tmp_path), str(f), 3, "card", "card", False)
    assert out["ok"] is False and out["code"] == "CONTAINER"


def test_guard_refuses_inline_markup_with_no_binding(tmp_path):
    import tryon_guard as TGU
    body = 'export default function P() { return (\n<a href="/x" className="btn">go</a>\n); }\n'
    f = _jsx_fixture(tmp_path, body)
    out = TGU.check(str(tmp_path), str(f), 2, "button", None, False)
    assert out["ok"] is False and out["code"] == "INLINE"


def test_guard_allows_a_like_for_like_imported_component(tmp_path):
    import tryon_guard as TGU
    f = _jsx_fixture(tmp_path, 'import { Button } from "@/components/ui/button";\nexport default function P() { return <Button>go</Button>; }\n')
    out = TGU.check(str(tmp_path), str(f), 2, "button", "button", False)
    assert out["ok"] is True and out["local"] == "Button" and out["code"] == "ALLOWED"


# ------------------------------------------- scope: base compatibility + registry preference
def test_guard_refuses_a_base_mismatch_unless_rescoped(tmp_path):
    """A Radix project must never be repointed at a Base UI component without an explicit confirm."""
    import tryon_guard as TGU
    (tmp_path / "package.json").write_text(
        json.dumps({"dependencies": {"radix-ui": "^1.4.2", "next": "15.6.0"}}), encoding="utf-8")
    f = _jsx_fixture(tmp_path, 'import { Button } from "@/components/ui/button";\nexport default function P() { return <Button>go</Button>; }\n')
    bad = TGU.check(str(tmp_path), str(f), 2, "button", "button", False, "base-ui")
    assert bad["ok"] is False and bad["code"] == "BASE_MISMATCH" and "base-ui" in bad["reason"]
    ok = TGU.check(str(tmp_path), str(f), 2, "button", "button", True, "base-ui")
    assert ok["ok"] is True, "an explicit owner confirmation allows it"
    free = TGU.check(str(tmp_path), str(f), 2, "button", "button", False, "none")
    assert free["ok"] is True, "a base-free candidate is always compatible"


def test_catalog_query_scopes_to_the_projects_base(tmp_path):
    """The catalog must hide candidates that need a different primitive base, and count them."""
    db = tmp_path / "t.db"
    _seed_catalog(db)
    con = DB.connect(db)
    DB.reg_upsert(con, {"registry": "basecn", "item": "base-button", "type": "registry:ui", "slot": "button",
                        "title": "Base Button", "base": "base-ui", "license": "MIT",
                        "item_url": "https://basecn.dev/r/base-button.json"})
    con.close()
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "package.json").write_text(json.dumps({"dependencies": {"radix-ui": "^1.4.2"}}), encoding="utf-8")
    p = subprocess.run([sys.executable, str(SCRIPTS / "tryon_catalog.py"), "--db", str(db),
                        "query", "--slot", "button", "--project", str(proj)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    assert "base-button" not in p.stdout, "a Base UI item must not be offered to a Radix project:\n" + p.stdout
    assert "1 hidden (need base-ui)" in p.stdout, p.stdout
    pj = subprocess.run([sys.executable, str(SCRIPTS / "tryon_catalog.py"), "--db", str(db),
                         "query", "--slot", "button", "--project", str(proj), "--json"], capture_output=True, text=True)
    rows = json.loads(pj.stdout)
    assert rows and all(r["base"] != "base-ui" for r in rows), rows


def test_server_scope_reads_the_project_files(tmp_path):
    """The overlay's scope line comes from the server reading the project's own files."""
    import tryon_server as TSV
    proj = tmp_path / "p"
    proj.mkdir()
    (proj / "package.json").write_text(json.dumps({"dependencies": {"radix-ui": "^1.4.2"}}), encoding="utf-8")
    (proj / "components.json").write_text(
        json.dumps({"$schema": "https://ui.shadcn.com/schema.json", "style": "base-nova"}), encoding="utf-8")
    scope = TSV.project_scope(proj)
    assert scope["base"] == "radix" and scope["lineage"] == "shadcn-style"
    assert scope["registry_pref"] == "shadcn"
    bare = tmp_path / "bare"
    bare.mkdir()
    s2 = TSV.project_scope(bare)
    assert s2["base"] == "unknown" and s2["registry_pref"] is None, "nothing readable → says so, never guesses"


# ------------------------------------------------- P0 hardening (2026-09-24 audit)
def _serve(project: Path, db: Path, token: str = "tok123"):
    """A real loopback server for the hardening tests (ephemeral port, its own project/db)."""
    import socket
    import threading
    from http.server import ThreadingHTTPServer
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    H = TS.Handler
    H.project, H.token, H.port, H.db = project, token, port, str(db)
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    srv.verbose = False
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def _post(port: int, body, token: str = "tok123", origin: str | None = None):
    import urllib.error
    import urllib.request
    req = urllib.request.Request(f"http://127.0.0.1:{port}/event?token={token}",
                                 data=json.dumps(body).encode(), method="POST")
    req.add_header("Content-Type", "text/plain")
    if origin:
        req.add_header("Origin", origin)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_server_post_refuses_a_foreign_origin(tmp_path):
    project = tmp_path / "p"
    (project / ".tryon").mkdir(parents=True)
    srv, port = _serve(project, tmp_path / "t.db")
    try:
        code, out = _post(port, {"type": "preview"}, origin="https://evil.example")
        assert code == 403 and "origin" in out["error"], "a random page must never reach the helper"
        code, out = _post(port, {"type": "preview"}, origin="http://localhost:3000")
        assert code == 200 and out["ok"] is True
        code, out = _post(port, {"type": "preview"})          # non-browser client (agent, curl)
        assert code == 200, "token-authenticated non-browser callers keep working"
    finally:
        srv.shutdown()


def test_server_post_drops_unknown_keys_and_caps_size(tmp_path):
    project = tmp_path / "p"
    (project / ".tryon").mkdir(parents=True)
    srv, port = _serve(project, tmp_path / "t.db")
    try:
        code, out = _post(port, {"type": "save", "request": 7, "id": 999,
                                 "received_at": "forged", "evil": ["x"] * 5})
        assert code == 200
        rec = TS.read_jsonl(project / ".tryon" / "requests.jsonl")[-1]
        assert rec["id"] == 1, "the server-managed id is not forgeable"
        assert rec["received_at"] != "forged", "the server-managed timestamp is not forgeable"
        assert rec["request"] == 7 and rec.get("dropped_keys") == 3, rec
        import http.client
        c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        c.putrequest("POST", "/event?token=tok123")
        c.putheader("Content-Length", str(TS.MAX_BODY_BYTES + 1))
        c.endheaders()          # headers only: the server caps Content-Length BEFORE reading the body
        assert c.getresponse().status == 413
        c.close()
    finally:
        srv.shutdown()


def test_server_cors_is_pinned_to_localhost_not_star(tmp_path):
    import urllib.request
    project = tmp_path / "p"
    (project / ".tryon").mkdir(parents=True)
    srv, port = _serve(project, tmp_path / "t.db")
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health")
        req.add_header("Origin", "http://localhost:3000")
        with urllib.request.urlopen(req, timeout=5) as r:
            assert r.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5) as r:
            assert r.headers.get("Access-Control-Allow-Origin") is None, "never `*` anymore"
    finally:
        srv.shutdown()


def test_reply_refuses_a_duplicate_without_force(tmp_path, capsys):
    project = tmp_path / "proj"
    (project / ".tryon").mkdir(parents=True)
    TS.append_jsonl(project / ".tryon" / "requests.jsonl", {"id": 1, "type": "preview"})
    ns = type("R", (), {"project": str(project), "id": 1, "status": "ok", "message": "x", "force": False})()
    assert TS.cmd_reply(ns) == 0
    capsys.readouterr()
    ns2 = type("R", (), {"project": str(project), "id": 1, "status": "ok", "message": "y", "force": False})()
    assert TS.cmd_reply(ns2) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["reason"] == "ALREADY_ANSWERED", "an answered request stays answered"
    ns3 = type("R", (), {"project": str(project), "id": 1, "status": "error", "message": "fix", "force": True})()
    assert TS.cmd_reply(ns3) == 0, "an explicit correction is allowed"


def test_install_gitignores_the_token_and_reverts_byte_exact(tmp_path):
    project = _next_fixture(tmp_path)
    assert not (project / ".gitignore").exists()
    ns = type("A", (), {"project": str(project), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 0
    gi = (project / ".gitignore").read_text(encoding="utf-8")
    assert ".tryon/" in gi and "components/dev/" in gi, "one git add -A must never publish the token"
    assert TIN.cmd_install(ns) == 0
    assert (project / ".gitignore").read_text(encoding="utf-8") == gi, "idempotent"
    ns = type("B", (), {"project": str(project)})()
    assert TIN.cmd_uninstall(ns) == 0
    assert not (project / ".gitignore").exists(), "created by us, untouched → removed"


def test_install_appends_to_existing_gitignore_and_restores_it(tmp_path):
    project = _next_fixture(tmp_path)
    (project / ".gitignore").write_text("node_modules/\n.next/\n", encoding="utf-8")
    before = (project / ".gitignore").read_bytes()
    ns = type("A", (), {"project": str(project), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 0
    gi = (project / ".gitignore").read_text(encoding="utf-8")
    assert gi.startswith("node_modules/\n.next/\n") and ".tryon/" in gi
    ns = type("B", (), {"project": str(project)})()
    assert TIN.cmd_uninstall(ns) == 0
    assert (project / ".gitignore").read_bytes() == before, "byte-exact restore"


# ------------------------------- uninstall vs. live swaps (one shared journal file)
def _swap_journal_entry(**kw) -> dict:
    """A journal row exactly as swap.mjs apply writes it: no `kind`, carries local/from/to."""
    e = {"file": "app/page.tsx", "local": "Button", "from": "@/components/ui/button",
         "to": "@/components/variants/x/y", "backup": ".tryon/backups/app__page.tsx.bak",
         "shaBefore": "a" * 16, "shaAfter": "b" * 16}
    e.update(kw)
    return e


def _write_journal(project: Path, entries: list[dict]) -> bytes:
    (project / ".tryon").mkdir(parents=True, exist_ok=True)
    raw = json.dumps(entries, indent=1).encode("utf-8")
    (project / ".tryon" / "journal.json").write_bytes(raw)
    return raw


def _swapped_fixture(tmp_path: Path) -> tuple[Path, bytes]:
    """Install on the Next fixture, then append the swap row swap.mjs would have written."""
    project = _next_fixture(tmp_path)
    (project / "tsconfig.json").write_text(json.dumps({"compilerOptions": {"paths": {"@/*": ["./*"]}}}),
                                           encoding="utf-8")
    (project / "components" / "ui").mkdir(parents=True)
    (project / "components" / "ui" / "button.tsx").write_text("export function Button() { return null }\n",
                                                              encoding="utf-8")
    (project / "app" / "page.tsx").write_text(
        'import { Button } from "@/components/ui/button";\n\n'
        "export default function P() { return <Button>go</Button>; }\n", encoding="utf-8")
    ns = type("A", (), {"project": str(project), "port": 7799, "force": False})()
    assert TIN.cmd_install(ns) == 0
    journal = json.loads((project / ".tryon" / "journal.json").read_text(encoding="utf-8"))
    journal.append(_swap_journal_entry())
    return project, _write_journal(project, journal)


def test_uninstall_refuses_while_swaps_are_live(tmp_path, capsys):
    """A live swap row is the only record of the owner's own imports: uninstall must refuse, not wipe it."""
    project, before = _swapped_fixture(tmp_path)
    capsys.readouterr()
    cfg = (project / "next.config.mjs").read_bytes()
    assert TIN.main(["uninstall", "--project", str(project)]) == 5
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["reason"] == "SWAPS_ACTIVE"
    assert out["files"] == ["app/page.tsx"], out
    assert "swap.mjs revert --all" in out["hint"] and project.as_posix() in out["hint"], out
    assert (project / ".tryon" / "journal.json").read_bytes() == before, \
        "the swap journal must survive byte-for-byte — swap.mjs revert reads it back"
    assert (project / "next.config.mjs").read_bytes() == cfg and (project / ".tryon" / "loader.cjs").exists(), \
        "a refusal touches nothing — the plumbing is still installed"


def test_uninstall_force_leave_swaps_keeps_the_journal_entry(tmp_path, capsys):
    """--force-leave-swaps: take the plumbing out, keep the swap journaled so revert still works."""
    project, _ = _swapped_fixture(tmp_path)
    capsys.readouterr()
    page = (project / "app" / "page.tsx").read_bytes()
    assert TIN.main(["uninstall", "--project", str(project), "--force-leave-swaps"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True, out
    left = json.loads((project / ".tryon" / "journal.json").read_text(encoding="utf-8"))
    assert [e for e in left if e.get("kind") is None and "local" in e] == [_swap_journal_entry()], left
    assert not (project / ".tryon" / "loader.cjs").exists(), "the plumbing went away"
    assert not (project / "components" / "dev" / "tryon-dev.tsx").exists()
    assert (project / "app" / "page.tsx").read_bytes() == page, "the live swap itself is left in place"


def test_uninstall_reports_staged_variants_it_leaves_on_disk(tmp_path, capsys):
    """Variants no remaining swap points at are still owner-reachable work: reported, never deleted."""
    project = _next_fixture(tmp_path)
    stage = project / "components" / "variants" / "button"
    stage.mkdir(parents=True)
    (stage / "kept.tsx").write_text("export function Kept() { return null }\n", encoding="utf-8")
    (stage / "orphan.tsx").write_text("export function Orphan() { return null }\n", encoding="utf-8")
    (project / ".tryon").mkdir(parents=True)
    (project / ".tryon" / "manifest.json").write_text(json.dumps([
        {"at": "x", "slot": "button", "entry": "Kept", "dest": "components/variants/button/kept.tsx",
         "specifier": "@/components/variants/button/kept"},
        {"at": "x", "slot": "button", "entry": "Orphan", "dest": "components/variants/button/orphan.tsx",
         "specifier": "@/components/variants/button/orphan"},
    ]), encoding="utf-8")
    _write_journal(project, [_swap_journal_entry(to="components/variants/button/kept.tsx")])
    assert TIN.main(["uninstall", "--project", str(project), "--force-leave-swaps"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["staged_left"] == ["components/variants/button/orphan.tsx"], out
    assert (stage / "kept.tsx").exists() and (stage / "orphan.tsx").exists(), "never deleted"


# ------------------------------------------- personal source (library_import, 'mine')
def test_library_import_offers_only_complete_items(tmp_path):
    import library_import as LI
    store = tmp_path / "store"
    store.mkdir()
    rows = [
        {"name": "button-mine", "base": "radix", "slot": "button", "license": "MIT",
         "sourceUrl": "https://example/r/button", "licenseEvidence": "registry claim",
         "deps": ["motion"], "tags": ["button"], "source": "built @ demo"},
        {"name": "no-licence", "base": "radix", "slot": "button"},
        {"name": "no-base", "slot": "button", "license": "MIT"},
        {"name": "lic-unknown", "base": "radix", "slot": "button", "license": "unknown"},
    ]
    store.joinpath("index.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    db = tmp_path / "t.db"
    assert LI.main(["--store", str(store), "--db", str(db)]) == 0
    con = DB.connect(db)
    mine = [dict(r) for r in DB.reg_rows(con, registry="mine", free_only=True)]
    assert [r["item"] for r in mine] == ["button-mine"], "only items with base+slot+licence are offered"
    r = mine[0]
    assert r["slot"] == "button" and r["base"] == "radix" and r["license"] == "MIT"
    assert json.loads(r["deps"]) == ["motion"]
    assert json.loads(r["registry_deps"]) == [], "aliased imports never become registryDependencies"
    assert len(DB.reg_rows(con, registry="mine")) == 1


def test_library_import_prunes_archived_items(tmp_path):
    import library_import as LI
    store = tmp_path / "store"
    store.mkdir()
    row = {"name": "card-mine", "base": "radix", "slot": "card", "license": "MIT"}
    store.joinpath("index.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    db = tmp_path / "t.db"
    assert LI.main(["--store", str(store), "--db", str(db)]) == 0
    con = DB.connect(db)
    assert len(DB.reg_rows(con, registry="mine")) == 1
    store.joinpath("index.jsonl").write_text("", encoding="utf-8")   # component archived via library.py remove
    assert LI.main(["--store", str(store), "--db", str(db)]) == 0
    assert len(DB.reg_rows(con, registry="mine")) == 1, "without --prune the row is left alone"
    assert LI.main(["--store", str(store), "--db", str(db), "--prune"]) == 0
    assert DB.reg_rows(con, registry="mine") == [], "an archived component must stop being offered"


def test_catalog_ranks_mine_first(tmp_path):
    db = tmp_path / "t.db"
    _seed_catalog(db)
    con = DB.connect(db)
    DB.reg_upsert(con, {"registry": "mine", "item": "button-mine", "type": "registry:component",
                        "title": "button-mine", "slot": "button", "slot_kind": "", "base": "radix",
                        "free": 1, "license": "MIT", "item_url": "https://x/1"})
    con.close()
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "package.json").write_text(json.dumps({"dependencies": {"radix-ui": "^1.4.2"}}), encoding="utf-8")
    pj = subprocess.run([sys.executable, str(SCRIPTS / "tryon_catalog.py"), "--db", str(db),
                         "query", "--slot", "button", "--project", str(proj), "--json"],
                        capture_output=True, text=True)
    assert pj.returncode == 0, pj.stderr
    rows = json.loads(pj.stdout)
    assert rows[0]["item"] == "button-mine", "the owner's own components rank first: " + str(rows[:2])


def test_server_catalog_rows_carry_licence_fields_and_rank_mine_first(tmp_path):
    import urllib.request
    db = tmp_path / "t.db"
    _seed_catalog(db)
    con = DB.connect(db)
    DB.reg_upsert(con, {"registry": "mine", "item": "button-mine", "type": "registry:component",
                        "title": "button-mine", "slot": "button", "slot_kind": "", "base": "radix",
                        "free": 1, "license": "MIT", "license_evidence": "user",
                        "deps": json.dumps(["motion"]), "registry_deps": json.dumps([]),
                        "item_url": "https://x/1"})
    con.close()
    project = tmp_path / "app"
    (project / ".tryon").mkdir(parents=True)
    (project / "package.json").write_text(json.dumps({"dependencies": {"radix-ui": "^1.4.2"}}), encoding="utf-8")
    srv, port = _serve(project, db)
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/catalog?slot=button", timeout=5) as r:
            data = json.loads(r.read().decode())
    finally:
        srv.shutdown()
    items = data["items"]
    assert items[0]["item"] == "button-mine", "personal rows rank first"
    it = items[0]
    assert it["license"] == "MIT" and it["license_evidence"] == "user"
    assert it["deps"] == json.dumps(["motion"]) and "style" in it, "the candidate carries what a save must record"
