#!/usr/bin/env python3
"""test_tryon_agent — the acceptance suite for tryon_agent.py handle.

One request in, one transaction out. These tests run the REAL pipeline end to end against a
throwaway project + a seeded catalog + a local registry server (port 0 — OS-assigned, outside the
Windows excluded ranges): guard -> catalog -> fetch -> stage -> props -> apply, and the
save / accept / revert verbs.

They need Node + the project's own TypeScript, like the swap battery: set TRYON_TS_ROOT to a
project whose node_modules has typescript@5. Without it every test skips.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parents[1]          # skills/buildout
SCRIPTS = HERE / "scripts"
AGENT = SCRIPTS / "tryon_agent.py"

sys.path.insert(0, str(SCRIPTS))
import templates_db as DB  # noqa: E402
import tryon_agent as TGA  # noqa: E402

TS_ROOT = os.environ.get("TRYON_TS_ROOT", "")
needs_ts = pytest.mark.skipif(
    not TS_ROOT or not (Path(TS_ROOT) / "node_modules" / "typescript").exists(),
    reason="no TypeScript root (set TRYON_TS_ROOT to a project with node_modules/typescript)")

PAGE = ('import { Button } from "@/components/ui/button";\n'
        "\n"
        "export function P() {\n"
        '  return <Button onClick={() => {}}>Book this trip</Button>;\n'
        "}\n")

SECTION = ('export function Section() {\n'
           "  return (\n"
           '    <div className="grid">\n'
           "      {items.map((i) => (<span key={i}>{i}</span>))}\n"
           "    </div>\n"
           "  );\n"
           "}\n")

BUTTON_SRC = ('import type { ComponentProps } from "react";\n'
              "\n"
              'export function ShimmerButton({ className, children, ...props }: ComponentProps<"button">) {\n'
              "  return (\n"
              "    <button className={className} {...props}>{children}</button>\n"
              "  );\n"
              "}\n")

DEMO_SRC = ('export default function DemoButton() {\n'
            '  return <button className="demo">Fixed content</button>;\n'
            "}\n")


def _item(name: str, content: str, url: str, **kw) -> dict:
    base = {"name": name, "type": "registry:ui", "title": name.title(), "description": "",
            "dependencies": [], "registryDependencies": [],
            "files": [{"path": "ui/%s.tsx" % name, "type": "registry:ui", "content": content}]}
    base.update(kw)
    base["_url"] = url
    return base


def serve_items(items: dict) -> tuple[str, list, ThreadingHTTPServer]:
    """A local registry: GET /<name>.json -> the item JSON. Records every hit."""
    hits: list = []

    class H(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            hits.append(self.path)
            name = self.path.rsplit("/", 1)[-1].removesuffix(".json")
            body = next((it for k, it in items.items() if k == name), None)
            if body is None:
                self.send_response(404)
                self.end_headers()
                return
            data = json.dumps({k: v for k, v in body.items() if k != "_url"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *a):  # quiet: the hits list is the log
            pass

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return "http://127.0.0.1:%d" % srv.server_address[1], hits, srv


def make_project(tmp_path: Path) -> Path:
    proj = tmp_path / "proj"
    (proj / "app").mkdir(parents=True)
    (proj / "components" / "ui").mkdir(parents=True)
    (proj / ".tryon").mkdir()
    (proj / "components" / "ui" / "button.tsx").write_text(
        "export function Button({ children }: { children?: React.ReactNode }) "
        "{ return <button>{children}</button>; }\n", encoding="utf-8")
    (proj / "app" / "page.tsx").write_text(PAGE, encoding="utf-8")
    (proj / "app" / "section.tsx").write_text(SECTION, encoding="utf-8")
    (proj / "components.json").write_text(
        '{"$schema": "https://ui.shadcn.com/schema.json", "style": "new-york"}', encoding="utf-8")
    (proj / "package.json").write_text(
        json.dumps({"name": "fx", "dependencies": {"next": "16.0.0", "react": "19.0.0"}}),
        encoding="utf-8")
    (proj / "tsconfig.json").write_text(
        json.dumps({"compilerOptions": {"baseUrl": ".", "paths": {"@/*": ["./*"]}}}), encoding="utf-8")
    return proj


def seed_catalog(db: Path, base_url: str) -> None:
    con = DB.connect(db)
    for item, typ in (("shimmer-button", "registry:ui"), ("demo-button", "registry:example")):
        assert DB.reg_upsert(con, {
            "registry": "fixture", "item": item, "style": "", "type": typ, "title": item.title(),
            "description": "", "categories": "[]", "slot": "button", "slot_kind": "primitive",
            "base": "none", "deps": "[]", "registry_deps": "[]",
            "item_url": "%s/%s.json" % (base_url, item), "index_url": "",
            "free": 1, "license": "MIT", "license_evidence": "registry claim",
            "content_sha": "", "fetched_at": DB.now(), "updated_at": DB.now(),
        }) == "written"
    con.close()


def write_request(proj: Path, row: dict) -> None:
    with (proj / ".tryon" / "requests.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def run_handle(proj: Path, rid: int, db: Path, store: Path, *extra: str) -> tuple[int, dict]:
    env = {**os.environ, "TRYON_TS_ROOT": TS_ROOT, "DECKHAND_LIBRARY": str(store)}
    p = subprocess.run([sys.executable, str(AGENT), "--db", str(db), "handle",
                        "--project", str(proj), "--id", str(rid), *extra],
                       cwd=str(proj), env=env, capture_output=True, text=True, timeout=180)
    last = {}
    for line in reversed((p.stdout or "").strip().splitlines()):
        try:
            last = json.loads(line)
            break
        except Exception:
            continue
    return p.returncode, last


def replies(proj: Path) -> dict:
    out = {}
    p = proj / ".tryon" / "responses.jsonl"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                out[r["id"]] = r
    return out


def preview_row(rid: int, item: str, url: str, file: str = "app/page.tsx", line: int = 4) -> dict:
    return {"id": rid, "type": "preview", "element": {"file": file, "line": line, "tag": "Button",
            "text": "Book this trip", "selector": ""}, "slot": "button",
            "candidate": {"registry": "fixture", "item": item, "item_url": url, "base": "none",
                          "license": "MIT"}}


@needs_ts
def test_preview_flips_the_import_and_records_six_steps(tmp_path):
    proj = make_project(tmp_path)
    items = {"shimmer-button": _item("shimmer-button", BUTTON_SRC, "")}
    base, hits, srv = serve_items(items)
    db, store = tmp_path / "cat.db", tmp_path / "store"
    seed_catalog(db, base)
    try:
        write_request(proj, preview_row(1, "shimmer-button", "%s/shimmer-button.json" % base))
        code, out = run_handle(proj, 1, db, store)
        assert code == 0 and out.get("ok") is True, out
        page = (proj / "app" / "page.tsx").read_text(encoding="utf-8")
        assert 'from "@/components/variants/button/shimmer-button"' in page
        assert "ShimmerButton as Button" in page
        r = replies(proj)
        assert r[1]["status"] == "ok" and "Undo restores bytes exactly" in r[1]["message"]
        tx = [json.loads(l) for l in (proj / ".tryon" / "transactions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        assert tx[-1]["id"] == 1 and tx[-1]["outcome"] == "ok"
        assert [s["name"] for s in tx[-1]["steps"]] == ["guard", "catalog", "fetch", "stage", "props", "apply"]
        assert all(s["exit"] == 0 for s in tx[-1]["steps"])
    finally:
        srv.shutdown()


@needs_ts
def test_preview_of_a_demo_item_is_refused_and_writes_nothing(tmp_path):
    proj = make_project(tmp_path)
    items = {"demo-button": _item("demo-button", DEMO_SRC, "")}
    base, hits, srv = serve_items(items)
    db, store = tmp_path / "cat.db", tmp_path / "store"
    seed_catalog(db, base)
    try:
        before = (proj / "app" / "page.tsx").read_bytes()
        write_request(proj, preview_row(1, "demo-button", "%s/demo-button.json" % base))
        code, out = run_handle(proj, 1, db, store)
        assert code == 1 and out.get("outcome") == "refused", out
        r = replies(proj)
        assert r[1]["status"] == "error" and "props: drops-content" in r[1]["message"], r.get(1)
        assert (proj / "app" / "page.tsx").read_bytes() == before
    finally:
        srv.shutdown()


@needs_ts
def test_guard_refuses_a_section_before_any_network_call(tmp_path):
    proj = make_project(tmp_path)
    items = {"shimmer-button": _item("shimmer-button", BUTTON_SRC, "")}
    base, hits, srv = serve_items(items)
    db, store = tmp_path / "cat.db", tmp_path / "store"
    seed_catalog(db, base)
    try:
        write_request(proj, preview_row(1, "shimmer-button", "%s/shimmer-button.json" % base,
                                        file="app/section.tsx", line=3))
        code, out = run_handle(proj, 1, db, store)
        assert code == 1 and out.get("outcome") == "refused", out
        r = replies(proj)
        assert r[1]["status"] == "error" and "guard" in r[1]["message"] and "CONTAINER" in r[1]["message"], r.get(1)
        assert hits == [], "a refused request must not fetch anything: %r" % hits
    finally:
        srv.shutdown()


@needs_ts
def test_save_after_preview_lands_in_the_store_and_catalog_mine(tmp_path):
    proj = make_project(tmp_path)
    items = {"shimmer-button": _item("shimmer-button", BUTTON_SRC, "")}
    base, hits, srv = serve_items(items)
    db, store = tmp_path / "cat.db", tmp_path / "store"
    seed_catalog(db, base)
    try:
        write_request(proj, preview_row(1, "shimmer-button", "%s/shimmer-button.json" % base))
        code, out = run_handle(proj, 1, db, store)
        assert code == 0, out
        write_request(proj, {"id": 2, "type": "save", "request": 1,
                             "element": {"file": "app/page.tsx", "line": 4},
                             "candidate": {"registry": "fixture", "item": "shimmer-button"}})
        code, out = run_handle(proj, 2, db, store)
        assert code == 0 and out.get("ok") is True, out
        assert (store / "items" / "shimmer-button").is_dir(), "the item is in the store"
        mine = store / "catalog-mine.db"
        assert mine.exists(), "personal rows live beside the store, never in the tracked db"
        con = DB.connect(mine)
        rows = [r["item"] for r in con.execute(
            "SELECT item FROM registry_items WHERE registry = 'mine'").fetchall()]
        con.close()
        assert "shimmer-button" in rows
        assert replies(proj)[2]["status"] == "ok"
    finally:
        srv.shutdown()


@needs_ts
def test_accept_empties_the_journal(tmp_path):
    proj = make_project(tmp_path)
    items = {"shimmer-button": _item("shimmer-button", BUTTON_SRC, "")}
    base, hits, srv = serve_items(items)
    db, store = tmp_path / "cat.db", tmp_path / "store"
    seed_catalog(db, base)
    try:
        write_request(proj, preview_row(1, "shimmer-button", "%s/shimmer-button.json" % base))
        assert run_handle(proj, 1, db, store)[0] == 0
        j = json.loads((proj / ".tryon" / "journal.json").read_text(encoding="utf-8"))
        assert len(j) == 1 and j[0]["local"] == "Button"
        write_request(proj, {"id": 2, "type": "accept",
                             "element": {"file": "app/page.tsx", "line": 4},
                             "candidate": {"registry": "fixture", "item": "shimmer-button"}})
        code, out = run_handle(proj, 2, db, store)
        assert code == 0 and out.get("ok") is True, out
        assert json.loads((proj / ".tryon" / "journal.json").read_text(encoding="utf-8")) == []
        man = json.loads((proj / ".tryon" / "manifest.json").read_text(encoding="utf-8"))
        assert any(m.get("kept") for m in man), "the manifest marks the graduated try"
        assert replies(proj)[2]["status"] == "ok"
    finally:
        srv.shutdown()


@needs_ts
def test_duplicate_handle_is_already_answered(tmp_path):
    proj = make_project(tmp_path)
    items = {"shimmer-button": _item("shimmer-button", BUTTON_SRC, "")}
    base, hits, srv = serve_items(items)
    db, store = tmp_path / "cat.db", tmp_path / "store"
    seed_catalog(db, base)
    try:
        write_request(proj, preview_row(1, "shimmer-button", "%s/shimmer-button.json" % base))
        assert run_handle(proj, 1, db, store)[0] == 0
        code, out = run_handle(proj, 1, db, store)
        assert code == 1 and out.get("reason") == "ALREADY_ANSWERED", out
    finally:
        srv.shutdown()


def test_deps_cmd_resolves_the_launcher(tmp_path):
    """Live regression (real project run): a bare `npm i` spawn died with [WinError 2].

    On Windows PATH carries `npm.cmd`; the installer must resolve the launcher to a real
    executable (shutil.which), or every --install-deps run refuses with INSTALL_FAILED.
    """
    (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
    exe = shutil.which("npm")
    if not exe:
        pytest.skip("npm is not on PATH on this machine")
    cmd = TGA.dep_cmd(tmp_path)
    assert cmd[1] == "i", "a package-lock project installs with npm i"
    assert cmd[0] == exe and Path(cmd[0]).exists(), "the launcher is the resolved real file"
    (tmp_path / "pnpm-lock.yaml").write_text("", encoding="utf-8")
    if shutil.which("pnpm"):
        assert TGA.dep_cmd(tmp_path)[1] == "add", "pnpm projects install with pnpm add"


def test_fetch_refuses_non_https_and_oversized_items(tmp_path):
    """Item URLs come from the catalog, but a tampered row must not become file:// or a remote http GET."""
    for url in ("file:///C:/Windows/win.ini", "http://example.com/item.json", "ftp://x/y.json"):
        with pytest.raises(ValueError, match="URL_NOT_ALLOWED"):
            TGA.fetch_item(url)
    base, _, srv = serve_items({"big": {"files": [{"path": "x.tsx", "content": "x" * (TGA.MAX_ITEM_BYTES + 10)}]}})
    try:
        with pytest.raises(ValueError, match="ITEM_TOO_LARGE"):
            TGA.fetch_item(base + "/big.json")
    finally:
        srv.shutdown()


def test_deps_refuse_anything_but_plain_npm_names(tmp_path):
    """A registry item's `dependencies` reach a package-manager argv: options, paths, URLs refuse."""
    (tmp_path / "package.json").write_text('{"dependencies": {"react": "19"}}', encoding="utf-8")
    for bad in ("--registry=https://evil.example", "../../x", "git+https://x/y.git", "https://x/y.tgz", "a b"):
        with pytest.raises(TGA.Refuse, match="BAD_DEP_NAME"):
            TGA.ensure_deps(tmp_path, [bad], True, [])
    TGA.ensure_deps(tmp_path, ["react@^19"], False, [])            # present by name -> no refusal
    with pytest.raises(TGA.Refuse, match="NEEDS_DEPS: @radix-ui/react-slot"):
        TGA.ensure_deps(tmp_path, ["@radix-ui/react-slot@1.1.0"], False, [])
    assert TGA.dep_name("@scope/pkg@1.2") == "@scope/pkg" and TGA.dep_name("lucide-react") == "lucide-react"
