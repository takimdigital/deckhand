"""dh — the Deckhand control plane. One JSON object per command on stdout; exit 0 = ok, 1 = check
failed / refused, 2 = usage. Run `dh next` whenever unsure: it prints the one next step."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .util import DhError, SKILL, TRYON, emit, project_root, read_json, write_json
from . import state as STATE


def _root(a) -> Path:
    return project_root(getattr(a, "project", None))


def _kv(pairs):
    out = {}
    for p in pairs:
        if "=" not in p:
            raise DhError("BAD_PAIR", f"expected key=value, got {p!r}")
        k, v = p.split("=", 1)
        out[k.strip()] = v
    return out


def cmd_brief(a):
    root = _root(a)
    path = root / ".deckhand" / "brief.json"
    b = read_json(path, None) or json.loads((SKILL / "templates" / "brief.json").read_text(encoding="utf-8"))
    if a.action == "set":
        for k, v in _kv(a.pairs).items():
            val = [x.strip() for x in v.split(",") if x.strip()] if k in ("languages", "features", "assumed", "template_names") else v
            cur = b
            parts = k.split(".")
            for p in parts[:-1]:
                cur = cur.setdefault(p, {})
            cur[parts[-1]] = val
        write_json(path, b)
    return b


def build_parser():
    ap = argparse.ArgumentParser(prog="dh", description="Deckhand control plane — `dh next` tells you what to do.")
    ap.add_argument("--project", help="project folder (default: nearest with .deckhand/ or package.json)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", default=argparse.SUPPRESS, help=argparse.SUPPRESS)   # accepted after the subcommand too
    sub = ap.add_subparsers(dest="cmd", required=True)
    _add = sub.add_parser
    sub.add_parser = lambda *a, **k: _add(*a, parents=[common], **k)  # type: ignore[method-assign]

    p = sub.add_parser("init"); p.add_argument("--name", required=True); p.add_argument("--mode", default="phased", choices=STATE.MODES); p.add_argument("--path", default="pool", choices=STATE.PATHS)
    sub.add_parser("status"); sub.add_parser("next")
    p = sub.add_parser("brief"); p.add_argument("action", choices=["show", "set"]); p.add_argument("pairs", nargs="*")
    p = sub.add_parser("phase"); p.add_argument("action", choices=["done", "skip"]); p.add_argument("phase", choices=STATE.PHASE_IDS)
    p.add_argument("--reason"); p.add_argument("--force", help="record done despite a red check (the reason is kept and shown)")
    p = sub.add_parser("gate"); p.add_argument("action", choices=["pass"]); p.add_argument("gate"); p.add_argument("--note", default="")
    p = sub.add_parser("reopen"); p.add_argument("phase", choices=STATE.PHASE_IDS); p.add_argument("--reason", required=True)

    p = sub.add_parser("profile"); p.add_argument("action", choices=["show", "set", "doctor"]); p.add_argument("pairs", nargs="*"); p.add_argument("--offline", action="store_true")
    p = sub.add_parser("vault"); p.add_argument("action", choices=["set", "list"]); p.add_argument("name", nargs="?")

    p = sub.add_parser("pool"); p.add_argument("action", choices=["query", "show", "vet", "add", "list", "sync"]); p.add_argument("target", nargs="?")
    p.add_argument("--shape"); p.add_argument("--features"); p.add_argument("--languages"); p.add_argument("--top", type=int, default=3); p.add_argument("--mine", action="store_true"); p.add_argument("--lane", default="web")

    p = sub.add_parser("plan"); p.add_argument("action", choices=["init", "lint", "render", "split"]); p.add_argument("--agents", type=int, default=3); p.add_argument("--force", action="store_true")
    p = sub.add_parser("bb"); p.add_argument("action", choices=["post", "read"]); p.add_argument("--wp", default="all"); p.add_argument("--kind", default="note"); p.add_argument("--msg"); p.add_argument("--last", type=int, default=40)

    p = sub.add_parser("clone"); p.add_argument("template"); p.add_argument("--to", required=True); p.add_argument("--no-install", action="store_true")
    p = sub.add_parser("adopt"); p.add_argument("source"); p.add_argument("--to"); p.add_argument("--install", action="store_true")
    p = sub.add_parser("scaffold"); p.add_argument("--to", required=True); p.add_argument("--pm", default="npm", choices=["npm", "pnpm", "bun", "yarn"])
    p = sub.add_parser("compose"); p.add_argument("--page", default="app/page.tsx"); p.add_argument("--sections", default="hero,features,pricing,faq,cta,footer"); p.add_argument("--copy")
    p = sub.add_parser("dev"); p.add_argument("action", choices=["start", "stop", "status"]); p.add_argument("--port", type=int)

    p = sub.add_parser("rebrand"); p.add_argument("action", choices=["scan", "apply", "check"]); p.add_argument("pairs", nargs="*"); p.add_argument("--dry", action="store_true"); p.add_argument("--allow", default="")
    p = sub.add_parser("swap"); p.add_argument("action", choices=["scan", "check"])
    p = sub.add_parser("verify"); p.add_argument("--url"); p.add_argument("--skip", default=""); p.add_argument("--allow", default="")

    p = sub.add_parser("deploy"); p.add_argument("action", choices=["target", "ship", "smoke", "raw"]); p.add_argument("rest", nargs=argparse.REMAINDER)
    p.add_argument("--app"); p.add_argument("--url"); p.add_argument("--force", action="store_true")
    p = sub.add_parser("ops"); p.add_argument("action", choices=["suggest", "add", "list"]); p.add_argument("bot", nargs="?"); p.add_argument("--runner", default="github")

    p = sub.add_parser("learn"); p.add_argument("action", choices=["add", "match", "preflight", "promote", "from-failure", "list"])
    p.add_argument("--phase", default="build"); p.add_argument("--symptom"); p.add_argument("--cause", default=""); p.add_argument("--fix", default="")
    p.add_argument("--signature"); p.add_argument("--command"); p.add_argument("--rung", default="pitfall"); p.add_argument("--scope", default="global")
    p.add_argument("--log"); p.add_argument("--text"); p.add_argument("--stack", default="")
    p = sub.add_parser("run"); p.add_argument("--phase"); p.add_argument("--fix", action="store_true", help="replay a proven auto-safe recipe, retry once")
    p.add_argument("argv", nargs=argparse.REMAINDER)
    p = sub.add_parser("autopsy", help="deterministic session analysis: failures -> recipes, lessons, skill proposals, playbooks")
    p.add_argument("source", nargs="?", help="a Claude Code transcript .jsonl or a run log (default: .deckhand/runs.jsonl, else the latest transcript)")
    p.add_argument("--latest", action="store_true"); p.add_argument("--apply", action="store_true")

    p = sub.add_parser("harvest"); p.add_argument("--name", required=True); p.add_argument("--to"); p.add_argument("--repo"); p.add_argument("--public", action="store_true")
    p.add_argument("--push", action="store_true", help="secret scan, then a private repo on your GitHub + your library index")
    sub.add_parser("handoff")
    p = sub.add_parser("tryon", help="passthrough to the try-on engine (node)"); p.add_argument("rest", nargs=argparse.REMAINDER)
    return ap


def dispatch(a):
    root = _root(a)
    c = a.cmd
    if c == "init":
        return STATE.init(root, a.name, a.mode, a.path)
    if c == "status":
        s = STATE.load(root)
        return {**STATE.summary(root, s), "phases": {k: v["status"] for k, v in s["phases"].items()}, "gates": {k: v["status"] for k, v in s["gates"].items()}, "base": s.get("base")}
    if c == "next":
        from . import guide
        return guide.next_step(root)
    if c == "brief":
        return cmd_brief(a)
    if c == "phase":
        if a.action == "skip":
            return STATE.phase_skip(root, a.phase, a.reason or "")
        r = STATE.phase_done(root, a.phase, force_reason=a.force)
        if not r["ok"]:
            raise DhError("CHECK_FAILED", f"phase {a.phase} is not done yet", check=r["check"])
        return r
    if c == "gate":
        return STATE.gate_pass(root, a.gate, a.note)
    if c == "reopen":
        return STATE.reopen(root, a.phase, a.reason)
    if c == "profile":
        from . import profile as PR
        if a.action == "set":
            return PR.set_fields(a.pairs)
        if a.action == "doctor":
            return PR.doctor(online=not a.offline)
        return {"profile": PR.load(), "path": str(PR.profile_path())}
    if c == "vault":
        from . import profile as PR
        if a.action == "list":
            return {"names": sorted(PR.vault_read()), "path": str(PR.vault_path())}
        if not a.name:
            raise DhError("USAGE", "dh vault set NAME   (value on stdin or prompted — never on the command line)")
        return PR.vault_set(a.name)
    if c == "pool":
        from . import pool as POOL
        if a.action == "query":
            brief = read_json(root / ".deckhand" / "brief.json", {}) or {}
            if a.shape: brief["shape"] = a.shape
            if a.features: brief["features"] = [x.strip() for x in a.features.split(",")]
            if a.languages: brief["languages"] = [x.strip() for x in a.languages.split(",")]
            brief["lane"] = a.lane
            return POOL.query(brief, a.top)
        if a.action == "show":
            return POOL.show(a.target)
        if a.action == "sync":
            from . import harvest as H
            return H.library_sync()
        if a.action in ("vet", "add") and not a.target:
            raise DhError("USAGE", f"dh pool {a.action} owner/repo")
        if a.action == "vet":
            return POOL.vet(a.target, mine=a.mine)
        if a.action == "add":
            return POOL.add(a.target, mine=a.mine, shape=a.shape, features=[x.strip() for x in (a.features or "").split(",") if x.strip()])
        return {"templates": [{k: r.get(k) for k in ("name", "source", "shape", "lane", "license", "stars")} for r in POOL.rows()]}
    if c == "plan":
        from . import plan as PL
        if a.action == "init":
            return PL.init(root, a.force)
        if a.action == "lint":
            r = PL.lint(root)
            if not r["ok"]:
                raise DhError("PLAN_ERRORS", f"{len(r['errors'])} errors in the plan", **r)
            return r
        if a.action == "render":
            return PL.render(root)
        return PL.split(root, a.agents)
    if c == "bb":
        from . import plan as PL
        if a.action == "post":
            if not a.msg:
                raise DhError("USAGE", "--msg required")
            return PL.bb_post(root, a.wp, a.kind, a.msg)
        return {"entries": PL.bb_read(root, None if a.wp == "all" else a.wp, None if a.kind == "note" else a.kind, a.last)}
    if c in ("clone", "adopt", "scaffold", "compose", "dev"):
        from . import build as B
        if c == "clone":
            return B.clone(a.template, Path(a.to), do_install=not a.no_install)
        if c == "adopt":
            return B.adopt(a.source, Path(a.to) if a.to else None, do_install=a.install)
        if c == "scaffold":
            return B.scaffold(Path(a.to), a.pm)
        if c == "compose":
            return B.compose(root, a.page, [s.strip() for s in a.sections.split(",")], a.copy)
        return {"start": lambda: B.dev_start(root, a.port), "stop": lambda: B.dev_stop(root), "status": lambda: B.dev_status(root)}[a.action]()
    if c == "rebrand":
        from . import brand as BR
        if a.action == "scan":
            return BR.scan(root)
        if a.action == "apply":
            brand = {k.replace("brand.", ""): v for k, v in _kv(a.pairs).items()}
            return BR.apply(root, brand, dry=a.dry)
        r = BR.check(root, allow=tuple(x for x in a.allow.split(",") if x))
        if not r["ok"]:
            raise DhError("LEAKS", f"{r['blocking']} blocking findings", **r)
        return r
    if c == "swap":
        from . import swap as SW
        if a.action == "scan":
            return SW.scan(root)
        r = SW.check(root)
        if not r["ok"]:
            raise DhError("SWAP_INCOMPLETE", "a vendor SDK is still in the code", **r)
        return r
    if c == "verify":
        from . import verify as V
        r = V.run_verify(root, a.url, skip=tuple(x for x in a.skip.split(",") if x), allow=tuple(x for x in a.allow.split(",") if x))
        if not r["ok"]:
            raise DhError("VERIFY_FAILED", "blocking rows are red (see .deckhand/VERIFY.md)", **r)
        return r
    if c == "deploy":
        from . import deploy as D
        if a.action == "target":
            return D.target(root, a.app, a.url)
        if a.action == "ship":
            return D.ship(root, force=a.force)
        if a.action == "smoke":
            sm = D.smoke(root, a.url)
            if not sm["ok"]:
                raise DhError("SMOKE_FAILED", sm["evidence"], smoke=sm)
            return sm
        return {"exit": D.passthrough(a.rest)}
    if c == "ops":
        from . import ops as O
        if a.action == "suggest":
            return O.suggest(root)
        if a.action == "list":
            return {"bots": O.catalog()}
        if not a.bot:
            raise DhError("USAGE", "dh ops add <bot-id> [--runner github|cron]")
        return O.add(root, a.bot, a.runner)
    if c == "learn":
        from . import learn as LE
        r_ = root if (root / ".deckhand").exists() else None
        if a.action == "add":
            if not a.symptom or not a.fix:
                raise DhError("USAGE", "--symptom and --fix are required")
            return LE.add(r_, a.phase, a.symptom, a.cause, a.fix, a.signature, a.command, a.rung, a.scope, [x for x in a.stack.split(",") if x])
        if a.action == "match":
            text = Path(a.log).read_text(encoding="utf-8", errors="replace") if a.log else (a.text or sys.stdin.read())
            return {"known_fixes": LE.match(r_, text)}
        if a.action == "preflight":
            return {"phase": a.phase, "lessons": LE.preflight(r_, a.phase)}
        if a.action == "promote":
            return LE.promote(r_)
        if a.action == "from-failure":
            return LE.from_failure(root, a.fix, a.cause, a.rung, a.scope, a.command)
        return {"lessons": LE.all_lessons(r_)}
    if c == "run":
        from . import learn as LE
        argv = a.argv[1:] if a.argv and a.argv[0] == "--" else a.argv
        r = LE.run_cmd(root, argv, a.phase, fix=a.fix)
        if not r["ok"]:
            raise DhError("COMMAND_FAILED", f"exit {r['code']}", exit=r["code"], **{k: v for k, v in r.items() if k not in ("code", "ok")})
        return r
    if c == "autopsy":
        from . import autopsy as AU
        return AU.autopsy(root, a.source, latest=a.latest, apply=a.apply)
    if c == "harvest":
        from . import harvest as H
        return H.harvest(root, a.name, Path(a.to) if a.to else None, a.repo, private=not a.public, push=a.push)
    if c == "handoff":
        from . import handoff as HO
        return HO.write(root)
    if c == "tryon":
        node = shutil.which("node")
        if not node:
            raise DhError("NO_NODE", "try-on needs Node.js 18+")
        rest = a.rest[1:] if a.rest and a.rest[0] == "--" else a.rest
        if "--project" not in rest:
            rest = rest[:1] + ["--project", str(root)] + rest[1:]
        return {"exit": subprocess.call([node, str(TRYON / "cli.mjs"), *rest])}
    raise DhError("USAGE", c)


def _log(a, shown: str, code: int, out: str = "") -> None:
    """Every dh call lands in .deckhand/runs.jsonl (phase transitions make the playbooks `dh autopsy` learns)."""
    if a.cmd in ("run", "autopsy", "next", "status"):
        return                                           # `run` logs itself; read-only calls are noise
    try:
        from . import learn as LE
        LE.log_run(_root(a), shown, code, out)
    except Exception:  # noqa: BLE001 — logging never breaks a command
        pass


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")        # Windows consoles default to cp1252
    except Exception:
        pass
    ap = build_parser()
    a = ap.parse_args(argv)
    shown = "dh " + " ".join(argv if argv is not None else sys.argv[1:])
    try:
        out = dispatch(a)
        if a.cmd == "tryon":
            _log(a, shown, out.get("exit", 0))
            return out.get("exit", 0)
        _log(a, shown, 0)
        return emit({"ok": True, **out} if isinstance(out, dict) else {"ok": True, "result": out})
    except DhError as e:
        _log(a, shown, 1, f"{e.code}: {e.message}")
        return emit({**e.extra, "ok": False, "code": e.code, "message": e.message}, 1)   # extra never overrides the verdict
    except KeyboardInterrupt:
        return emit({"ok": False, "code": "INTERRUPTED"}, 130)
