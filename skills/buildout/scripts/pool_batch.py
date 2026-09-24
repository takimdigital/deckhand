#!/usr/bin/env python3
"""pool_batch.py — the owner sent repos: one plan, AT MOST THREE measuring agents, one import.

The rule this script exists to enforce: a batch of repos is measured by at most 3 subagents, each
carrying a slice of the list — never one agent per repo. The measuring contract lives in
`references/pool-details-contract.md`; the importer (and everything it validates) is
`templates_db.py import-details`, which this script reuses rather than reimplements.

usage:
  py scripts/pool_batch.py plan --file repos.txt [--agents 3] [--id <batch>]
  py scripts/pool_batch.py check  <batch> [--json]
  py scripts/pool_batch.py import <batch>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import templates_db as DB  # noqa: E402

SKILL_DIR = Path(__file__).resolve().parent.parent
DEFAULT_INBOX = SKILL_DIR / "data" / "details-inbox"
DEFAULT_STORE = SKILL_DIR / "data" / "details"
CONTRACT = SKILL_DIR / "references" / "pool-details-contract.md"
MAX_AGENTS = 3

REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*$")
URL_RE = re.compile(r"^(?:https?://(?:www\.)?github\.com/|git@github\.com:)([^/\s]+/[^/\s]+?)(?:\.git)?/?$")


# ---------------------------------------------------------------- parsing
def parse_repos(text: str) -> tuple[list[str], list[str]]:
    """`owner/name` list from pasted text. Blank lines/comments ignored; duplicates collapsed."""
    repos: list[str] = []
    errs: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip().strip(",;").strip()
        if not line:
            continue
        m = URL_RE.match(line)
        slug = (m.group(1) if m else line).rstrip("/").strip()
        if not REPO_RE.match(slug):
            errs.append(f"not a GitHub repo (want `owner/name` or a github.com URL): {line}")
            continue
        if slug.lower() in seen:
            continue
        seen.add(slug.lower())
        repos.append(slug)
    return repos, errs


def slice_repos(repos: list[str], agents: int) -> list[list[str]]:
    """Even round-robin slices. Never more agents than repos, never more than MAX_AGENTS."""
    n = max(1, min(agents, MAX_AGENTS, len(repos)))
    return [repos[i::n] for i in range(n)]


def _registry(db: Path) -> dict[str, dict]:
    """What the registry already knows per repo — so a batch never spends an agent on a repo the
    pool has already refused (no license) or on re-deciding a row that is already measured."""
    if not db.exists():
        return {}
    con = DB.connect(db)
    try:
        return {(r["repo"] or "").lower(): {"name": r["name"], "license_ok": r["license_ok"],
                                            "status": r["status"], "license": r["license_spdx"]}
                for r in con.execute("SELECT name, repo, license_ok, status, license_spdx FROM templates")}
    finally:
        con.close()


def _known_repos(db: Path) -> set[str]:
    return set(_registry(db))


def _slug(repo: str) -> str:
    return repo.split("/", 1)[1].lower()


# ---------------------------------------------------------------- plan
def _agent_block(i: int, total: int, batch_id: str, files_dir: Path, slice_: list[str]) -> str:
    n = len(slice_)
    noun = "repository" if n == 1 else "repositories"
    listing = "\n".join(f"  {k}. {r}  ->  {files_dir / (_slug(r) + '.json')}" for k, r in enumerate(slice_, 1))
    return f"""── delegate_task task {i}/{total} — {n} repo(s) ─────────────────────────────
goal: Measure {n} GitHub {noun} in depth through the GitHub API and write ONE JSON
file per repo (paths below), following the contract at {CONTRACT}. These are {i}/{total} of a batch
pool intake (batch {batch_id}); the other agents handle the rest. Finish your answer with, per file:
its path, its byte size, a one-line summary of each major section, and an explicit list of anything
you could NOT measure.

repos and output files (write each file the moment its repo is done, not at the end):
{listing}

context: You are ONE of {total} agents sharing this batch — do not spawn further agents, and do not
touch a repo outside your slice. Write ONLY the files listed above: no scratch, cache or working
files anywhere inside the skill directory (use your OS temp directory for anything else) — the skill
tree ships as a package and stray files are caught by a gate. Measure REMOTELY only: `gh api` (or `curl` with a browser UA) and
raw.githubusercontent — never clone, never install, never execute anything from these repos. Read the
contract file above first; it defines the exact JSON keys. Hard rules: environment variables by NAME
only, never values (a credential-shaped value means the file is rejected); every non-obvious fact
carries its `evidence` (file or URL); the only place for a use-stopping claim is `blocking[]`, which
must carry `kind` (`injected-payload` | `install-impossible`), `why` and `evidence` — and must be
re-measurable from the repo, not inferred from prose. Watch for: obfuscated/injected blobs, phantom
dependencies that 404, secrets committed in tracked files (record the NAME only), README claims the
code contradicts, build-time-required env vars, and dead/archived state. Budget ~2 minutes per repo.
"""


def cmd_plan(args: argparse.Namespace) -> int:
    src = Path(args.file)
    if not src.exists():
        print(f"plan: no such file: {src} — save the owner's repo list first (one repo per line)",
              file=sys.stderr)
        return 2
    text = src.read_text(encoding="utf-8")
    repos, errs = parse_repos(text)
    for e in errs:
        print(f"  refused: {e}", file=sys.stderr)
    if not repos:
        print("plan: nothing usable in that file — expected one `owner/name` or github.com URL per line",
              file=sys.stderr)
        return 2
    if args.agents > MAX_AGENTS:
        print(f"  note: --agents {args.agents} clamped to the {MAX_AGENTS}-agent rule for one batch")
    reg = _registry(Path(args.db))
    measurable, skipped = [], []
    for r in repos:
        row = reg.get(r.lower())
        if row and not row.get("license_ok"):
            skipped.append((r, row))
        else:
            measurable.append(r)
    if not measurable:
        for r, row in skipped:
            print(f"  skipped: {r} — the pool refuses it ({row.get('license') or 'no MIT/Apache-2.0'} "
                  f"license) and details cannot change that", file=sys.stderr)
        print("plan: nothing measurable in that list", file=sys.stderr)
        return 2
    slices = slice_repos(measurable, args.agents)
    batch_id = args.id or "b" + re.sub(r"[^0-9]", "", DB.now())[:14]
    bdir = Path(args.inbox) / batch_id
    files_dir = (bdir / "files")
    files_dir.mkdir(parents=True, exist_ok=True)
    (bdir / "repos.txt").write_text("\n".join(repos) + "\n", encoding="utf-8")
    known = set(reg)
    agent_of = {r: f"a{i + 1}" for i, s in enumerate(slices) for r in s}
    manifest = {
        "batch_id": batch_id, "created": DB.now(), "file": str(args.file), "agents": len(slices),
        # `repos` keeps the owner's order (the agent field says who measures it); `slices` is the
        # per-agent work list. Same data, two readings.
        "repos": [{"repo": r, "slug": _slug(r), "in_registry": r.lower() in known,
                   "measurable": r in measurable, "agent": agent_of.get(r)} for r in repos],
        "skipped": [{"repo": r, "why": f"pool refuses it ({row.get('license') or 'no MIT/Apache-2.0'} license)"}
                    for r, row in skipped],
        "slices": [{"agent": f"a{i + 1}", "repos": s} for i, s in enumerate(slices)],
        # snapshot of the skill root: children have dropped scratch files into the shipped tree
        # before (triply-repo.json, triply-langs.json), and a diff is the only thing that catches it.
        "root_before": sorted(p.name for p in SKILL_DIR.iterdir()),
    }
    (bdir / "batch.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    new = [r for r in measurable if r.lower() not in known]
    print(f"batch {batch_id} · {len(repos)} repo(s) sent · {len(measurable)} measurable · "
          f"{len(slices)} agent(s) · files -> {files_dir}")
    print(f"  already in the registry: {len(measurable) - len(new)} (they will be refreshed) · new: {len(new)}")
    for r in manifest["repos"]:
        state = "known" if r["in_registry"] else "NEW  "
        if not r["measurable"]:
            print(f"  REFUSED  {r['repo']:44} pool licence rule — no agent spent on it")
        else:
            print(f"  {state}  {r['repo']:44} agent {r['agent']}")
    if new:
        print("\n  new repos must be measured into the registry BEFORE import refuses to attach their"
              " details:\n    " + "\n    ".join(f"py scripts/template_intake.py --repo {r}" for r in new))
    for i, s in enumerate(slices, 1):
        print()
        print(_agent_block(i, len(slices), batch_id, files_dir, s))
    print(f"── after the agents finish ─────────────────────────────────────────")
    print(f"py scripts/pool_batch.py check {batch_id}")
    print(f"py scripts/pool_batch.py import {batch_id}")
    return 0


# ---------------------------------------------------------------- check
def _index_files(files_dir: Path) -> dict[str, tuple[Path | None, dict | None, list[str], list[str]]]:
    index: dict[str, tuple[Path | None, dict | None, list[str], list[str]]] = {}
    if not files_dir.exists():
        return index
    for f in sorted(files_dir.glob("*.json")):
        text = f.read_text(encoding="utf-8")
        try:
            rec = json.loads(text)
        except Exception as e:
            index[f.stem.lower()] = (f, None, [f"invalid JSON: {e}"], [])
            continue
        errs, warns = DB.validate_details(rec, text)
        key = (rec.get("repo") or "").lower() or f.stem.lower()
        entry = (f, rec, errs, warns)
        index[key] = entry
        # A file written for this repo but named differently (or broken before its `repo` could be
        # read) is still this repo's file — otherwise a broken file reports as MISSING and the agent
        # goes looking for something that is already on disk.
        slug = (rec.get("slug") or "").lower()
        if slug:
            index.setdefault(slug, entry)
    return index


def cmd_check(args: argparse.Namespace) -> int:
    bdir = Path(args.inbox) / args.batch
    mpath = bdir / "batch.json"
    if not mpath.exists():
        print(f"check: no batch {args.batch} under {Path(args.inbox)}", file=sys.stderr)
        return 2
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    index = _index_files(bdir / "files")
    known = _known_repos(Path(args.db))
    before = manifest.get("root_before")
    stray = (sorted(p.name for p in SKILL_DIR.iterdir() if p.name not in set(before))
             if before is not None else [])
    rows, bad = [], 0
    for r in manifest["repos"]:
        if not r.get("measurable", True):
            # The pool refused this repo (no MIT/Apache licence): no file will ever appear for it,
            # so it must not block the batch's gate.
            rows.append({"repo": r["repo"], "agent": "-", "state": "REFUSED",
                         "detail": "pool licence rule — never measured, nothing to import",
                         "warnings": []})
            continue
        entry = index.get(r["repo"].lower()) or index.get(r["slug"].lower(), (None, None, [], []))
        f, rec, errs, warns = entry
        if f is None:
            state, detail = "MISSING", f"expected files/{r['slug']}.json"
        elif errs:
            state, detail = "INVALID", "; ".join(errs)
        else:
            state, detail = "ok", f"{f.name} ({f.stat().st_size} B)"
        if r["repo"].lower() not in known:
            detail += f" · not in the registry: run template_intake.py --repo {r['repo']} first"
            if state == "ok":
                state = "NO ROW"
        if state != "ok":
            bad += 1
        rows.append({"repo": r["repo"], "agent": r["agent"], "state": state, "detail": detail,
                     "warnings": warns})
    if stray:
        bad += 1
    if args.json:
        print(json.dumps({"batch": args.batch, "rows": rows, "stray_root_files": stray},
                         ensure_ascii=False, indent=2))
    else:
        for x in rows:
            print(f"  {x['state']:8} {x['repo']:44} {x['agent']}  {x['detail']}")
        n_ok = sum(1 for x in rows if x["state"] == "ok")
        n_ref = sum(1 for x in rows if x["state"] == "REFUSED")
        ref_note = f" · {n_ref} refused by the pool licence rule" if n_ref else ""
        for x in rows:
            for w in x["warnings"]:
                print(f"  warn   {x['repo']}: {w}")
        if stray:
            shown = ", ".join(stray[:6]) + (f" (+{len(stray) - 6} more)" if len(stray) > 6 else "")
            print(f"  STRAY    {len(stray)} file(s) dropped into the skill root since plan: {shown}")
            print("           delete them — they would ship inside the pack; children write only to files/")
        print(f"check: {n_ok}/{len(rows) - n_ref} measurable repo(s) ready{ref_note} · "
              f"{'ALL READY — import it' if not bad else 'NOT ready — fix the rows above'}")
    return 0 if not bad else 3


# ---------------------------------------------------------------- import
def cmd_import(args: argparse.Namespace) -> int:
    bdir = Path(args.inbox) / args.batch
    files_dir = bdir / "files"
    if not (bdir / "batch.json").exists():
        print(f"import: no batch {args.batch} under {Path(args.inbox)}", file=sys.stderr)
        return 2
    if not files_dir.exists() or not list(files_dir.glob("*.json")):
        print(f"import: nothing to import — {files_dir} has no *.json", file=sys.stderr)
        return 2
    con = DB.connect(Path(args.db))
    try:
        code = DB.cmd_import_details(con, files_dir, Path(args.store), False)
        with_details = con.execute("SELECT count(*) c FROM templates WHERE details IS NOT NULL").fetchone()["c"]
        blocked = []
        for row in con.execute("SELECT name, risk_flags FROM templates ORDER BY name"):
            flags = json.loads(row["risk_flags"] or "[]")
            if any(f.get("kind") in DB.BLOCKING_KINDS for f in flags):
                blocked.append(row["name"])
        print(f"\nregistry now: {with_details} template(s) with details · "
              f"blocked: {', '.join(blocked) or '-'}")
    finally:
        con.close()
    return code


def main() -> int:
    ap = argparse.ArgumentParser(description="Batch pool intake (plan · check · import).")
    ap.add_argument("--db", default=str(DB.DEFAULT_DB))
    ap.add_argument("--inbox", default=str(DEFAULT_INBOX))
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="validate the owner's repo list and slice it for <=3 agents")
    p.add_argument("--file", required=True, help="text file with one repo per line (URLs or owner/name)")
    p.add_argument("--agents", type=int, default=MAX_AGENTS, help=f"1..{MAX_AGENTS} (default {MAX_AGENTS})")
    p.add_argument("--id", default=None, help="batch id (default: from the clock)")
    p.set_defaults(fn=cmd_plan)

    c = sub.add_parser("check", help="validate every file of a batch before importing")
    c.add_argument("batch")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_check)

    i = sub.add_parser("import", help="fold a batch's detail files into the registry")
    i.add_argument("batch")
    i.add_argument("--store", default=str(DEFAULT_STORE))
    i.set_defaults(fn=cmd_import)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
