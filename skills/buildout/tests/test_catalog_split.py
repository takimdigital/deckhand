"""T06b — personal ('mine') rows never share a file with the shipped catalog.

F6: `library_import` wrote the owner's free-text `--source` into the git-tracked, binary
`data/templates.db` — invisible to a text sweep, permanent in git history. Personal rows now live in
`<store>/catalog-mine.db` and are joined read-only at query time (TEMP VIEW `all_items`).

(a) connect_catalog attaches when catalog-mine.db exists and `all_items` is queryable, and the
    shipped DB still holds only shipped rows;
(b) library_import --db <explicit> still writes wherever it is told (the migration/test path), and
    the default write path lands in the mine DB — never in the shipped DB;
(c) with no catalog-mine.db, readers keep working on the plain connection (no attach, no view).
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
SHIPPED = SKILL / "data" / "templates.db"
sys.path.insert(0, str(SCRIPTS))

import templates_db as DB  # noqa: E402


def run(script: str, *args, store: Path | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if store is not None:
        env["DECKHAND_LIBRARY"] = str(store)
    return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)],
                          capture_output=True, text=True, env=env)


def item(registry: str, name: str, **kw) -> dict:
    rec = {"registry": registry, "item": name, "style": "", "type": "registry:component",
           "title": name, "description": "fixture", "categories": "[]", "slot": "button",
           "slot_kind": "primitive", "base": "radix", "deps": "[]", "registry_deps": "[]",
           "item_url": f"https://example.test/r/{name}.json", "index_url": "", "free": 1,
           "license": "MIT", "license_evidence": "", "content_sha": "",
           "fetched_at": DB.now(), "updated_at": DB.now()}
    rec.update(kw)
    return rec


def make_store(store: Path, name: str = "t06b-button", source: str = "fixture source") -> Path:
    """A minimal but real index.jsonl — exactly the keys `library.py add` writes."""
    store.mkdir(parents=True, exist_ok=True)
    (store / "index.jsonl").write_text(json.dumps({
        "name": name, "tags": ["cta"], "section": "", "files": [f"items/{name}/{name}.tsx"],
        "deps": [], "imports": [], "fileHashes": {}, "license": "MIT",
        "sourceUrl": f"https://example.test/{name}", "licenseEvidence": "", "base": "radix",
        "slot": "button", "depVersions": [], "source": source, "createdAt": DB.now(),
    }) + "\n", encoding="utf-8")
    return store


def registries(rows) -> list[str]:
    return [r["registry"] for r in rows]


# ---------------------------------------------------------------- (a) attach + all_items
def test_connect_catalog_attaches_mine_and_all_items_is_queryable(tmp_path, monkeypatch):
    store = tmp_path / "store"
    monkeypatch.setenv("DECKHAND_LIBRARY", str(store))
    shipped = tmp_path / "templates.db"
    con = DB.connect(shipped)
    DB.reg_upsert(con, item("shadcn", "button"))
    con.close()

    # no mine DB yet: the plain connection must still work and carry no view
    plain = DB.connect_catalog(shipped)
    assert plain.execute("SELECT 1 FROM sqlite_temp_master WHERE name = 'all_items'").fetchone() is None
    assert registries(DB.reg_rows(plain, slot="button", base="radix")) == ["shadcn"]
    plain.close()

    assert DB.mine_db() == store / "catalog-mine.db"
    mcon = DB.connect(DB.mine_db())
    DB.reg_upsert(mcon, item("mine", "t06b-button"))
    mcon.close()

    cat = DB.connect_catalog(shipped)
    assert cat.execute("SELECT 1 FROM sqlite_temp_master WHERE name = 'all_items'").fetchone() is not None
    assert sorted(registries(cat.execute("SELECT * FROM all_items"))) == ["mine", "shadcn"]
    # reg_rows reads the view, so both DBs are visible through the one reader
    assert registries(DB.reg_rows(cat, slot="button", base="radix")) == ["mine", "shadcn"]
    cat.close()

    # personal rows were joined, never copied: the shipped file holds only its own row
    con = DB.connect(shipped)
    assert registries(con.execute("SELECT * FROM registry_items")) == ["shadcn"]
    con.close()


def test_writer_connection_still_sees_only_the_shipped_table(tmp_path, monkeypatch):
    """A plain connect() is the write path: it must never accidentally read the personal rows."""
    store = tmp_path / "store"
    monkeypatch.setenv("DECKHAND_LIBRARY", str(store))
    mcon = DB.connect(DB.mine_db())                                    # create the mine DB
    DB.reg_upsert(mcon, item("mine", "t06b-button"))
    mcon.close()
    shipped = tmp_path / "templates.db"
    con = DB.connect(shipped)
    DB.reg_upsert(con, item("shadcn", "button"))
    assert registries(DB.reg_rows(con, slot="button")) == ["shadcn"]
    con.close()


# ---------------------------------------------------------------- (b) explicit --db
def test_library_import_explicit_db_still_writes_where_told(tmp_path, monkeypatch):
    store = make_store(tmp_path / "store", source="fixture source")
    monkeypatch.setenv("DECKHAND_LIBRARY", str(store))
    target = tmp_path / "elsewhere" / "explicit.db"

    r = run("library_import.py", "--db", target, store=store)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["db"] == str(target) and out["written"] == 1, out

    con = DB.connect(target)
    rows = [dict(x) for x in con.execute("SELECT registry, item, description, license FROM registry_items")]
    con.close()
    assert rows == [{"registry": "mine", "item": "t06b-button",
                     "description": "fixture source", "license": "MIT"}]
    # explicit --db means the default mine DB was never created
    assert not DB.mine_db().exists()


def test_library_import_default_writes_the_mine_db_and_never_the_shipped_db(tmp_path, monkeypatch):
    store = make_store(tmp_path / "store", source="private owner text")
    monkeypatch.setenv("DECKHAND_LIBRARY", str(store))

    r = run("library_import.py", store=store)
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["db"] == str(store / "catalog-mine.db"), out
    assert (store / "catalog-mine.db").exists()

    if SHIPPED.exists():   # structural guard: the library has no write path into the tracked DB
        ro = sqlite3.connect(f"file:{SHIPPED.as_posix()}?mode=ro", uri=True)
        try:
            n = ro.execute("SELECT COUNT(*) FROM registry_items WHERE registry = 'mine'").fetchone()[0]
        finally:
            ro.close()
        assert n == 0, "personal rows are in the git-tracked shipped DB"


def test_tryon_catalog_query_merges_both_dbs_and_ranks_mine_first(tmp_path, monkeypatch):
    """The acceptance path end to end: import (no --db) → query finds the personal item first."""
    store = make_store(tmp_path / "store")
    monkeypatch.setenv("DECKHAND_LIBRARY", str(store))
    shipped = tmp_path / "templates.db"
    con = DB.connect(shipped)
    DB.reg_upsert(con, item("shadcn", "button"))
    con.close()
    assert run("library_import.py", store=store).returncode == 0

    r = run("tryon_catalog.py", "--db", shipped, "query", "--slot", "button",
            "--base", "radix", "--json", store=store)
    assert r.returncode == 0, r.stderr
    rows = json.loads(r.stdout)
    assert [x["registry"] for x in rows][:2] == ["mine", "shadcn"], rows


# ---------------------------------------------------------------- (c) no mine DB → no attach
def test_no_mine_db_means_plain_connection_no_attach(tmp_path, monkeypatch):
    store = tmp_path / "store"          # env points at a store dir that was never created
    monkeypatch.setenv("DECKHAND_LIBRARY", str(store))
    shipped = tmp_path / "templates.db"
    con = DB.connect(shipped)
    DB.reg_upsert(con, item("shadcn", "button"))
    con.close()

    r = run("tryon_catalog.py", "--db", shipped, "query", "--slot", "button",
            "--base", "radix", "--json", store=store)
    assert r.returncode == 0, r.stderr
    assert [x["registry"] for x in json.loads(r.stdout)] == ["shadcn"]

    cat = DB.connect_catalog(shipped)
    assert cat.execute("SELECT 1 FROM sqlite_temp_master WHERE name = 'all_items'").fetchone() is None
    with pytest.raises(sqlite3.OperationalError):
        cat.execute("SELECT * FROM all_items").fetchone()
    assert registries(DB.reg_rows(cat, slot="button")) == ["shadcn"]
    cat.close()
