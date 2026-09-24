#!/usr/bin/env python3
"""tryon_agent — one command per panel request (the transaction handler behind try-on).

    py scripts/tryon_agent.py handle --project D:/app --id N [--yes-unverifiable] [--install-deps]

Runs the whole transaction for ONE request from <project>/.tryon/requests.jsonl — guard -> scoped
catalog lookup -> fetch -> stage -> prop check -> apply (or save / keep / revert, by request type)
— writes the panel reply itself through tryon_server.cmd_reply and appends a record to
<project>/.tryon/transactions.jsonl. The agent is the relay: `tryon_server.py wait --follow` in the
background, `handle` per request line. An "ok" reply is unreachable except through every check
passing: the first failing step becomes the error reply's message and exit 1. Stdlib only.
"""
from __future__ import annotations

import argparse, contextlib, io, json, os, re, shutil, subprocess, sys, time, types
from pathlib import Path
from urllib.request import Request, urlopen

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
SWAP = SKILL / "templates" / "tryon" / "swap.mjs"
GUARD = HERE / "tryon_guard.py"
LIBRARY = SKILL.parent / "component-library" / "scripts" / "library.py"
IMPORT = HERE / "library_import.py"
LOCK_MANAGERS = [("pnpm-lock.yaml", ["pnpm", "add"]), ("package-lock.json", ["npm", "i"]),
                 ("yarn.lock", ["yarn", "add"])]

sys.path.insert(0, str(HERE))
import templates_db as DB  # noqa: E402
import tryon_catalog as CAT  # noqa: E402
import tryon_server as SRV  # noqa: E402


class Refuse(Exception):
    """A checked refusal: the step's name and the machine-readable reason."""
    def __init__(self, step: str, reason: str):
        super().__init__(reason)
        self.step, self.reason = step, reason


def now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def py_exe() -> str:
    return os.environ.get("TRYON_PYTHON") or sys.executable


def node_exe() -> str:
    return os.environ.get("TRYON_NODE") or "node"


def run(step: str, argv: list[str], cwd: Path) -> dict:
    """One subprocess step. Its exit code + last JSON line are the evidence record."""
    t0 = time.time()
    out, code, payload = "", 127, None
    try:
        p = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True, timeout=120)
        out, code = p.stdout.strip(), p.returncode
    except Exception as e:                                        # a spawn failure is a failed step
        out = str(e)
    for line in reversed(out.splitlines()):                       # last JSON line = the contract
        try:
            if line.strip().startswith("{"):
                payload = json.loads(line.strip())
                break
        except Exception:
            continue
    detail = (payload or {}).get("reason") or (payload or {}).get("code") or (payload or {}).get("error")
    if detail is None and out:
        detail = out.splitlines()[-1][:200]
    return {"name": step, "exit": code, "reason": detail, "ms": int((time.time() - t0) * 1000),
            "json": payload, "stdout": out}


def brief(steps: list[dict]) -> list[dict]:
    """The transactions.jsonl shape: names, exits, reasons, times — never raw stdout."""
    return [{"name": s["name"], "exit": s["exit"], "reason": s["reason"], "ms": s["ms"]} for s in steps]


def write_reply(project: Path, rid: int, status: str, message: str) -> bool:
    with contextlib.redirect_stdout(io.StringIO()):
        rc = SRV.cmd_reply(types.SimpleNamespace(project=str(project), id=int(rid),
                                                 status=status, message=message, force=False))
    return rc == 0


def journal_tx(project: Path, rec: dict) -> None:
    SRV.append_jsonl(SRV.state_dir(project) / "transactions.jsonl", rec)


def slug(s: str) -> str:
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", str(s))
    return re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()[:60] or "component"


def fetch_item(url: str) -> dict:
    req = Request(url, headers={"User-Agent": "deckhand-tryon/1.0 (+local dev overlay)"})
    with urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def pick_main_file(files: list[dict], item: str) -> dict:
    """The entry file: the one whose name matches the item, else the first file with code."""
    norm = lambda x: re.sub(r"[^a-z0-9]", "", str(x).lower())  # noqa: E731
    code = [f for f in files if re.search(r"\.(tsx|jsx|ts|js)$", str(f.get("path") or ""))]
    for f in code or files:
        if norm(item) and norm(item) in norm(Path(str(f.get("path"))).stem):
            return f
    return (code or files)[0]


def pick_entry(content: str) -> str | None:
    """The export to bind: the first named export, else `default`. Never a guess past that."""
    named = re.findall(r"export\s+(?:async\s+)?(?:function|class)\s+([A-Za-z_$][\w$]*)", content)
    named += re.findall(r"export\s+(?:const|let|var)\s+([A-Za-z_$][\w$]*)", content)
    for m in re.findall(r"export\s*\{([^}]*)\}", content):
        for part in m.split(","):
            name = part.split(" as ")[-1].strip() if " as " in part else part.strip()
            if re.match(r"^[A-Za-z_$][\w$]*$", name):
                named.append(name)
    if named:
        return named[0]
    return "default" if re.search(r"export\s+default\b", content) else None


def scoped_lookup(con, project: Path, slot: str, candidate: dict) -> dict:
    """The catalog row for the pick, under the project's hard base scope."""
    prof = CAT.project_profile(project)
    base = prof.get("base")
    filt = base if base in ("radix", "base-ui", "aria", "none") else None
    all_rows = [dict(r) for r in DB.reg_rows(con, slot=slot, base=None, free_only=True)]
    rows = [dict(r) for r in DB.reg_rows(con, slot=slot, base=filt, free_only=True)]
    hit = next((r for r in rows if r["registry"] == candidate.get("registry") and r["item"] == candidate.get("item")), None)
    if hit is None:
        out = next((r for r in all_rows if r["registry"] == candidate.get("registry") and r["item"] == candidate.get("item")), None)
        if out is not None:
            raise Refuse("catalog", "SCOPE_MISMATCH: %s/%s is built for base '%s' and this project is '%s' "
                                    "(the picker hides those; re-pick or confirm a re-scope)"
                                    % (candidate.get("registry"), candidate.get("item"), out.get("base"), base))
        raise Refuse("catalog", "CANDIDATE_NOT_IN_CATALOG: %s/%s is not an offerable item for slot '%s'"
                                % (candidate.get("registry"), candidate.get("item"), slot))
    return hit


def dep_cmd(project: Path) -> list[str]:
    """The install command for this project, launcher resolved to a real executable.

    Windows regression (hit live): PATH carries `npm.cmd`, not `npm` — a bare spawn without a
    shell dies with [WinError 2]. Resolve with shutil.which, exactly as scripts/_tpl_lib.py
    resolves `gh`.
    """
    cmd = next((c for lock, c in LOCK_MANAGERS if (project / lock).exists()), ["npm", "i"])
    exe = shutil.which(cmd[0])
    if not exe:
        raise Refuse("deps", "NPM_NOT_FOUND: %s is not on PATH — install the deps by hand" % cmd[0])
    return [exe, *cmd[1:]]


def ensure_deps(project: Path, item_deps: list[str], install: bool, steps: list[dict]) -> None:
    """R6: npm deps the item needs and the project lacks. Refuse by default; install only on flag."""
    if not item_deps:
        return
    proj: dict = {}
    pkg = project / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            proj = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
        except Exception:
            pass
    missing = [d for d in item_deps if d not in proj]
    if not missing:
        return
    if not install:
        raise Refuse("deps", "NEEDS_DEPS: %s (re-run with --install-deps, or the swap breaks at import)"
                             % ", ".join(missing))
    cmd = dep_cmd(project)
    keep = SRV.state_dir(project) / "backups"                     # the bytes the install will change
    keep.mkdir(parents=True, exist_ok=True)
    saved = []
    for name in ("package.json", "pnpm-lock.yaml", "package-lock.json", "yarn.lock"):
        if (project / name).exists():
            (keep / ("deps-%d-%s.bak" % (int(time.time()), name))).write_bytes((project / name).read_bytes())
            saved.append(name)
    s = run("deps", cmd + missing, project)
    steps.append(s)
    if s["exit"] != 0:
        raise Refuse("deps", "INSTALL_FAILED: %s %s" % (" ".join(cmd), s["reason"] or ""))
    SRV.append_jsonl(SRV.state_dir(project) / "deps-journal.jsonl",
                     {"at": now(), "cmd": cmd + missing, "saved": saved,
                      "restore": "copy .tryon/backups/deps-*.bak back over the original names"})


def do_preview(project: Path, req: dict, args) -> tuple[str, list[dict]]:
    element = req.get("element") or {}
    file, line = element.get("file"), int(element.get("line") or 0)
    slot = str(req.get("slot") or "").strip()
    cand = req.get("candidate") or {}
    if not file or not line or not slot or not cand.get("item"):
        raise Refuse("request", "MALFORMED_REQUEST: needs element.file/line, slot and candidate.item")
    steps: list[dict] = []

    # 1. guard — before ANY fetch or write (exit 4 = refused; the reason goes to the panel as-is)
    gargv = [py_exe(), str(GUARD), "check", "--project", str(project), "--file", str(file),
             "--line", str(line), "--candidate-slot", slot]
    if req.get("elementSlot"):
        gargv += ["--element-slot", str(req["elementSlot"])]
    if (cand.get("base") or "").strip():
        gargv += ["--candidate-base", str(cand["base"]).strip()]
    if req.get("rescope"):
        gargv += ["--rescope"]
    g = run("guard", gargv, project)
    steps.append(g)
    gj = g["json"] or {}
    if g["exit"] != 0 or not gj.get("ok"):
        raise Refuse("guard", "%s: %s" % (gj.get("code") or "REFUSED", gj.get("reason") or g["reason"] or ""))
    local = gj.get("local")
    if not local:
        raise Refuse("guard", "REFUSED: the guard allowed the swap but named no binding")

    # 2. scoped lookup (in-process: the same catalog the picker reads)
    con = DB.connect(Path(args.db))
    try:
        row = scoped_lookup(con, project, slot, cand)
    finally:
        con.close()
    steps.append({"name": "catalog", "exit": 0, "reason": None, "ms": 0,
                  "json": {"registry": row["registry"], "item": row["item"], "license": row.get("license")}})
    try:
        item_deps = json.loads(row.get("deps") or "[]")
    except Exception:
        item_deps = []
    ensure_deps(project, item_deps, args.install_deps, steps)

    # 3. fetch — the endpoint must embed files[].content (content-less items are skipped silently by
    #    the shadcn CLI; here that is a refusal, never a staged empty file)
    url = row.get("item_url") or ""
    if not url:
        raise Refuse("fetch", "NO_ITEM_URL: the catalog row has no fetchable endpoint")
    try:
        item = fetch_item(url)
    except Exception as e:
        raise Refuse("fetch", "FETCH_FAILED: %s (%s)" % (url, e))
    files = [f for f in (item.get("files") or []) if isinstance(f, dict) and f.get("content")]
    if not files:
        raise Refuse("fetch", "CONTENT_LESS_ITEM: %s returned no files[].content" % url)
    main = pick_main_file(files, row["item"])
    entry = pick_entry(str(main.get("content") or ""))
    if entry is None:
        raise Refuse("fetch", "NO_EXPORT_FOUND: %s exports nothing importable" % Path(str(main.get("path"))).name)
    tmpdir = SRV.state_dir(project) / "tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    tmp = tmpdir / ("fetch-%d-%s" % (args.id, Path(str(main.get("path"))).name or "item.tsx"))
    tmp.write_text(str(main["content"]), encoding="utf-8")
    steps.append({"name": "fetch", "exit": 0, "reason": None, "ms": 0,
                  "json": {"url": url, "files": len(files), "entry": entry}})

    # 4. stage — with the licence/origin evidence pinned into the manifest at stage time
    meta = {k: row.get(k) for k in ("registry", "item", "style", "base", "type", "title",
                                    "license", "license_evidence", "item_url")}
    meta = {**cand, **{k: v for k, v in meta.items() if v is not None}}
    metafile = tmpdir / ("meta-%d.json" % args.id)
    metafile.write_text(json.dumps({"request": args.id, "candidate": meta}, ensure_ascii=False), encoding="utf-8")
    as_name = slug(row["item"]) + (Path(str(main.get("path"))).suffix or ".tsx")
    s = run("stage", [node_exe(), str(SWAP), "install", "--root", str(project), "--from", str(tmp),
                      "--slot", slot, "--entry", entry, "--as", as_name,
                      "--request", str(args.id), "--meta-file", str(metafile)], project)
    steps.append(s)
    sj = s["json"] or {}
    if s["exit"] != 0 or not sj.get("ok"):
        raise Refuse("stage", sj.get("reason") or s["reason"] or "STAGE_FAILED")
    dest_rel = Path(sj["dest"]).relative_to(project).as_posix()

    # 5. prop check against the REAL usage — fit / missing / unverifiable is decided here
    p = run("props", [node_exe(), str(SWAP), "props", "--root", str(project), "--file", str(file),
                      "--line", str(line), "--local", local, "--candidate", dest_rel, "--entry", entry], project)
    steps.append(p)
    pj = p["json"] or {}
    if p["exit"] == 3:
        if not args.yes_unverifiable:
            raise Refuse("props", "UNVERIFIABLE_PROPS (%s): the panel cannot judge %s against this usage; "
                                  "re-run with --yes-unverifiable only if the owner confirms"
                                  % (pj.get("verdict") or "unverifiable", row["item"]))
    elif p["exit"] != 0 or pj.get("ok") is not True:
        extra = ""
        if pj.get("missing_required"):
            extra = " missing: " + ", ".join(pj["missing_required"])
        elif pj.get("behaviour_dropped"):
            extra = " would drop: " + ", ".join(pj["behaviour_dropped"])
        elif pj.get("dropped"):
            extra = " drops: " + ", ".join(pj["dropped"])
        raise Refuse("props", "%s%s" % (pj.get("verdict") or pj.get("reason") or "NOT_A_FIT", extra))

    # 6. apply — flip the one import; byte-exact backup + journal are written by swap.mjs
    a = run("apply", [node_exe(), str(SWAP), "apply", "--root", str(project), "--file", str(file),
                      "--line", str(line), "--local", local, "--to", sj["specifier"], "--entry", entry], project)
    steps.append(a)
    aj = a["json"] or {}
    if a["exit"] != 0 or not aj.get("ok"):
        raise Refuse("apply", aj.get("reason") or a["reason"] or "APPLY_FAILED")

    dropped = pj.get("dropped") or []
    msg = ("swapped %s in %s:%s -> %s/%s (licence %s)%s; Undo restores bytes exactly."
           % (local, file, line, row["registry"], row["item"], row.get("license") or "unknown",
              ("; props the new component ignores: " + ", ".join(dropped)) if dropped else ""))
    if p["exit"] == 3:
        msg = "(unverifiable props - owner confirmed) " + msg
    return msg, steps


def do_save(project: Path, req: dict, args) -> tuple[str, list[dict]]:
    ref = req.get("request")
    if ref is None:
        raise Refuse("save", "MALFORMED_REQUEST: save needs request=<preview id>")
    steps: list[dict] = []
    v = run("verify-stage", [node_exe(), str(SWAP), "verify-stage", "--root", str(project),
                             "--request", str(int(ref))], project)
    steps.append(v)
    vj = v["json"] or {}
    if v["exit"] != 0 or not vj.get("ok"):
        raise Refuse("verify-stage", vj.get("reason") or v["reason"] or "STAGE_NOT_VERIFIED")
    entry, cand = vj.get("entry") or {}, vj.get("candidate") or {}
    name = slug(cand.get("item") or Path(str(entry.get("dest"))).stem)
    argv = [py_exe(), str(LIBRARY), "add", "--name", name, "--file", str(project / str(entry.get("dest"))), "--strict"]
    if entry.get("slot"):
        argv += ["--tags", str(entry["slot"]), "--section", str(entry["slot"]), "--slot", str(entry["slot"])]
    for flag, key in (("--license", "license"), ("--source-url", "item_url"),
                      ("--license-evidence", "license_evidence"), ("--base", "base")):
        if cand.get(key):
            argv += [flag, str(cand[key])]
    argv += ["--source", "%s/%s" % (cand.get("registry") or "?", cand.get("item") or name)]
    l = run("library", argv, project)
    steps.append(l)
    if l["exit"] != 0:
        raise Refuse("library", (l["stdout"].splitlines() or [l["reason"] or "ADD_FAILED"])[-1])
    i = run("import", [py_exe(), str(IMPORT)], project)
    steps.append(i)
    ij = i["json"] or {}
    if i["exit"] != 0:
        raise Refuse("import", ij.get("reason") or i["reason"] or "IMPORT_FAILED")
    offered = ij.get("offered")
    msg = ("saved %s to your library (licence %s); it ranks first in the picker for slot '%s'%s."
           % (name, cand.get("license") or "unknown", entry.get("slot") or "",
              (" (%s items offered)" % offered) if offered is not None else ""))
    return msg, steps


def do_keep(project: Path, req: dict, args) -> tuple[str, list[dict]]:
    file = (req.get("element") or {}).get("file")
    if not file:
        raise Refuse("keep", "MALFORMED_REQUEST: keep needs element.file")
    k = run("keep", [node_exe(), str(SWAP), "keep", "--root", str(project), "--file", str(file)], project)
    kj = k["json"] or {}
    if k["exit"] != 0 or not kj.get("ok"):
        raise Refuse("keep", kj.get("reason") or k["reason"] or "KEEP_FAILED")
    deleted, kept = kj.get("deleted") or [], kj.get("kept_imported") or []
    msg = ("kept %s — it is project code now; cleared %d unused staged candidate(s)%s. "
           "Undo is a normal code edit from here, not a revert."
           % (kj.get("kept") or "the variant", len(deleted),
              ("; still used elsewhere: " + ", ".join(kept)) if kept else ""))
    return msg, [k]


def do_revert(project: Path, req: dict, args) -> tuple[str, list[dict]]:
    file = (req.get("element") or {}).get("file")
    if not file:
        raise Refuse("revert", "MALFORMED_REQUEST: revert needs element.file")
    r = run("revert", [node_exe(), str(SWAP), "revert", "--root", str(project), "--file", str(file)], project)
    rj = r["json"] or {}
    if r["exit"] != 0 or not rj.get("ok"):
        raise Refuse("revert", rj.get("reason") or r["reason"] or "REVERT_FAILED")
    first = (rj.get("results") or [{}])[0]
    return "reverted %s — bytes restored exactly (%s)." % (file, first.get("mode") or "restored"), [r]


def cmd_handle(args) -> int:
    project = Path(args.project).resolve()
    if not (project / ".tryon").exists():
        print(json.dumps({"ok": False, "reason": "NOT_INSTALLED",
                          "hint": "run tryon_install.py install --project <dir> first"}, ensure_ascii=False))
        return 1
    req = next((r for r in SRV.read_jsonl(SRV.state_dir(project) / "requests.jsonl")
                if int(r.get("id", -1)) == int(args.id)), None)
    if req is None:
        print(json.dumps({"ok": False, "reason": "NO_SUCH_REQUEST", "id": args.id}, ensure_ascii=False))
        return 1
    if int(args.id) in {r.get("id") for r in SRV.read_jsonl(SRV.state_dir(project) / "responses.jsonl")}:
        print(json.dumps({"ok": False, "reason": "ALREADY_ANSWERED", "id": args.id,
                          "hint": "reply --force appends a correction; handle never re-runs a request"},
                         ensure_ascii=False))
        return 1

    rtype = str(req.get("type") or "preview").lower()
    steps: list[dict] = []
    try:
        if rtype == "preview":
            msg, steps = do_preview(project, req, args)
        elif rtype == "save":
            msg, steps = do_save(project, req, args)
        elif rtype in ("accept", "keep"):
            msg, steps = do_keep(project, req, args)
        elif rtype == "revert":
            msg, steps = do_revert(project, req, args)
        elif rtype == "catalog":
            msg, steps = "catalog notice — the picker reads /catalog itself; nothing to do.", []
        else:
            raise Refuse("request", "BAD_REQUEST_TYPE: %s" % rtype)
    except Refuse as r:
        message = "%s: %s" % (r.step, r.reason)
        wrote = write_reply(project, int(args.id), "error", message)
        journal_tx(project, {"id": int(args.id), "type": rtype, "at": now(), "outcome": "refused",
                             "message": message, "steps": brief(steps)})
        print(json.dumps({"ok": False, "id": int(args.id), "type": rtype, "outcome": "refused",
                          "message": message, "replied": wrote, "steps": brief(steps)}, ensure_ascii=False))
        return 1
    wrote = write_reply(project, int(args.id), "ok", msg)
    journal_tx(project, {"id": int(args.id), "type": rtype, "at": now(), "outcome": "ok",
                         "message": msg, "steps": brief(steps)})
    print(json.dumps({"ok": True, "id": int(args.id), "type": rtype, "outcome": "ok",
                      "message": msg, "replied": wrote, "steps": brief(steps)}, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="try-on transaction handler (one command per panel request)")
    ap.add_argument("--db", default=str(DB.DEFAULT_DB))
    sub = ap.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("handle")
    h.add_argument("--project", required=True)
    h.add_argument("--id", type=int, required=True)
    h.add_argument("--yes-unverifiable", action="store_true",
                   help="proceed when the prop check says unverifiable (only after the owner confirms)")
    h.add_argument("--install-deps", action="store_true",
                   help="install the item's npm dependencies (journaled for revert); off by default")
    args = ap.parse_args(argv)
    return cmd_handle(args)


if __name__ == "__main__":
    sys.exit(main())
