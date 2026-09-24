"""pool_batch tests — the owner sends repos: <=3 agents, one plan, one import.

Offline: no network, no clone. The batch is driven through the real CLI with temp
inboxes/registries so nothing under the skill's own data/ is touched.
"""
from __future__ import annotations

import json
from pathlib import Path

from test_factory import _detail_file, registry, run  # noqa: F401  (fixture reuse)

INBOX = "inbox"


def _repos_file(tmp: Path, text: str) -> Path:
    tmp.mkdir(parents=True, exist_ok=True)
    p = tmp / "repos.txt"
    p.write_text(text, encoding="utf-8")
    return p


def _plan(tmp: Path, text: str, *extra: str, db: Path | None = None):
    f = _repos_file(tmp, text)
    return run("pool_batch.py", "--db", db or (tmp / "none.db"), "--inbox", tmp / INBOX,
               "plan", "--file", f, "--id", "b1", *extra)


def _manifest(tmp: Path) -> dict:
    return json.loads((tmp / INBOX / "b1" / "batch.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- plan
def test_plan_slices_a_batch_across_at_most_three_agents(tmp_path):
    r = _plan(tmp_path, "\n".join(f"acme/r{i}" for i in range(1, 9)))
    assert r.returncode == 0, r.stderr
    m = _manifest(tmp_path)
    assert m["agents"] == 3, "8 repos must go to 3 agents, never 8"
    sizes = sorted(len(s["repos"]) for s in m["slices"])
    assert sizes == [2, 3, 3], sizes
    flat = [r["repo"] for r in m["repos"]]
    assert flat == [f"acme/r{i}" for i in range(1, 9)] and len(flat) == 8
    assert "delegate_task task 1/3" in r.stdout and "delegate_task task 3/3" in r.stdout
    assert "do not spawn further agents" in r.stdout
    for repo in flat:                       # every repo is in exactly one slice
        assert len([s for s in m["slices"] if repo in s["repos"]]) == 1


def test_plan_clamps_the_agent_count_and_never_uses_more_agents_than_repos(tmp_path):
    r = _plan(tmp_path, "acme/a\nacme/b\nacme/c\nacme/d", "--agents", "5")
    assert r.returncode == 0
    assert "clamped to the 3-agent rule" in r.stdout
    assert _manifest(tmp_path)["agents"] == 3
    r = _plan(tmp_path / "two", "acme/a\nacme/b")
    assert r.returncode == 0
    assert _manifest(tmp_path / "two")["agents"] == 2, "2 repos must not produce 3 agents"


def test_plan_refuses_anything_that_is_not_a_github_repo(tmp_path):
    r = _plan(tmp_path, "https://gitlab.com/acme/thing\nthis is not a repo!!\n")
    assert r.returncode == 2, "a list with no usable repo must not produce a batch"
    assert "not a GitHub repo" in r.stderr
    assert not (tmp_path / INBOX / "b1").exists()
    # one bad line among good ones: the batch still runs, and the bad line is named
    r = _plan(tmp_path / "mixed", "https://gitlab.com/acme/thing\nacme/good")
    assert r.returncode == 0 and "gitlab.com" in r.stderr
    assert [x["repo"] for x in _manifest(tmp_path / "mixed")["repos"]] == ["acme/good"]


def test_plan_refuses_a_missing_input_file(tmp_path):
    r = run("pool_batch.py", "--inbox", tmp_path / INBOX, "plan", "--file", tmp_path / "nope.txt")
    assert r.returncode == 2 and "no such file" in r.stderr and "Traceback" not in r.stderr


def test_plan_normalises_urls_and_drops_duplicates(tmp_path):
    r = _plan(tmp_path, """
      # the owner's list
      https://github.com/Acme/Alpha.git
      acme/alpha          # same repo again
      git@github.com:acme/Beta
      https://github.com/acme/gamma/tree/main   # a tree URL is not a repo
    """)
    assert r.returncode == 0
    assert [x["repo"] for x in _manifest(tmp_path)["repos"]] == ["Acme/Alpha", "acme/Beta"]


def test_plan_marks_repos_already_in_the_registry_and_names_the_intake_for_new_ones(tmp_path, registry):
    db, _ = registry
    r = _plan(tmp_path, "acme/alpha\nacme/brand-new", db=db)
    assert r.returncode == 0
    m = {x["repo"]: x["in_registry"] for x in _manifest(tmp_path)["repos"]}
    assert m == {"acme/alpha": True, "acme/brand-new": False}
    assert "template_intake.py --repo acme/brand-new" in r.stdout


# ---------------------------------------------------------------- check
def test_check_reports_missing_invalid_and_unknown_rows(tmp_path, registry):
    db, _ = registry
    r = _plan(tmp_path, "acme/alpha\nacme/beta\nacme/ghost", db=db)
    assert r.returncode == 0
    files = tmp_path / INBOX / "b1" / "files"
    _detail_file(files, "alpha")                       # valid, repo acme/alpha, row exists
    (files / "beta.json").write_text("{not json", encoding="utf-8")
    r = run("pool_batch.py", "--db", db, "--inbox", tmp_path / INBOX, "check", "b1")
    assert r.returncode == 3, r.stdout
    assert "INVALID" in r.stdout and "beta" in r.stdout
    assert "MISSING" in r.stdout and "ghost" in r.stdout
    assert "NOT ready" in r.stdout


def test_check_is_green_when_every_file_validates(tmp_path, registry):
    db, _ = registry
    _plan(tmp_path, "acme/alpha", db=db)
    _detail_file(tmp_path / INBOX / "b1" / "files", "alpha")
    r = run("pool_batch.py", "--db", db, "--inbox", tmp_path / INBOX, "check", "b1")
    assert r.returncode == 0, r.stdout
    assert "1/1 ready" in r.stdout and "ALL READY" in r.stdout


def test_import_refuses_a_batch_with_no_files(tmp_path, registry):
    db, _ = registry
    _plan(tmp_path, "acme/alpha", db=db)
    r = run("pool_batch.py", "--db", db, "--inbox", tmp_path / INBOX, "import", "b1")
    assert r.returncode == 2 and "nothing to import" in r.stderr


# ---------------------------------------------------------------- import
def test_import_folds_the_batch_into_the_registry(tmp_path, registry):
    db, _ = registry
    _plan(tmp_path, "acme/alpha", db=db)
    _detail_file(tmp_path / INBOX / "b1" / "files", "alpha")
    r = run("pool_batch.py", "--db", db, "--inbox", tmp_path / INBOX,
            "import", "b1", "--store", tmp_path / "data" / "details")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "1 template(s) with details" in r.stdout
    listing = run("templates_db.py", "--db", db, "list", "--json")
    row = {x["name"]: x for x in json.loads(listing.stdout)}["alpha"]
    assert row["details"]["repo"] == "acme/alpha" and row["features"], row
    assert (tmp_path / "data" / "details" / "alpha.json").exists(), "the batch files land in the store"


def test_a_batch_file_with_a_poison_claim_becomes_a_blocker(tmp_path, registry):
    """The end-to-end promise: a batch that carries `blocking[]` turns the row into a hard blocker."""
    db, _ = registry
    _plan(tmp_path, "acme/alpha", db=db)
    _detail_file(tmp_path / INBOX / "b1" / "files", "alpha", blocking=[{
        "kind": "injected-payload", "why": "obfuscated blob welded onto an export line",
        "evidence": "postcss.config.mjs"}])
    assert run("pool_batch.py", "--db", db, "--inbox", tmp_path / INBOX, "import", "b1",
               "--store", tmp_path / "data" / "details").returncode == 0
    listing = run("templates_db.py", "--db", db, "list", "--json")
    row = {x["name"]: x for x in json.loads(listing.stdout)}["alpha"]
    kinds = [f["kind"] for f in row["risk_flags"]]
    assert "blocked" in kinds or "injected-payload" in kinds, row["risk_flags"]
