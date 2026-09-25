"""The run state machine: one file (.deckhand/run.json) says where a build is and what comes next.

Phases run in order. A phase is DONE only when its check (a script, never an opinion) passes.
In `phased` mode a gate after a phase blocks the next one until the owner says go
(`dh gate pass G1`); in `auto` mode gates pass themselves and are logged.
`dh next` prints ONE instruction + the ONE reference to load + the lessons for that phase:
the agent never needs to re-read the whole skill to know what to do.
"""
from __future__ import annotations

from pathlib import Path

from .util import DhError, now, read_json, write_json, append_jsonl, SKILL

PHASES = [
    {"id": "define", "title": "Define the business and the path", "ref": "references/00-define.md"},
    {"id": "research", "title": "Research: market, top competitors, audience, conversion", "ref": "references/10-research.md"},
    {"id": "plan", "title": "Plan: page map + feature wiring (no dead ends)", "ref": "references/20-plan.md", "gate": "G1"},
    {"id": "build", "title": "Build: clone / adopt / scaffold, run it locally", "ref": "references/30-build.md", "gate": "G2"},
    {"id": "brand", "title": "Rebrand to the plan", "ref": "references/40-brand.md"},
    {"id": "tryon", "title": "Try-on: swap sections for licensed variants", "ref": "references/50-tryon.md", "gate": "G3", "optional": True},
    {"id": "review", "title": "Review: build, routes, security, honesty", "ref": "references/60-review.md", "gate": "G4"},
    {"id": "deploy", "title": "Deploy + handoff", "ref": "references/70-deploy.md"},
    {"id": "operate", "title": "Operate: changes, bots, monitoring", "ref": "references/80-operate.md", "continuous": True},
]
PHASE_IDS = [p["id"] for p in PHASES]
GATES = {"G1": "the plan (page map + features) is approved",
         "G2": "the owner opened the local app and says go",
         "G3": "the design (brand + try-on) is approved",
         "G4": "go live: deploy to the server"}
MODES = ("phased", "auto")
PATHS = ("pool", "mine", "existing", "scratch")


def state_path(root: Path) -> Path:
    return Path(root) / ".deckhand" / "run.json"


def load(root: Path, required: bool = True) -> dict:
    s = read_json(state_path(root))
    if s is None and required:
        raise DhError("NO_RUN", f"no .deckhand/run.json in {root} — start with `dh init`")
    return s


def save(root: Path, s: dict) -> None:
    s["updated"] = now()
    write_json(state_path(root), s)


def log(root: Path, event: dict) -> None:
    append_jsonl(Path(root) / ".deckhand" / "history.jsonl", {"at": now(), **event})


def init(root: Path, name: str, mode: str = "phased", path: str = "pool") -> dict:
    if mode not in MODES:
        raise DhError("BAD_MODE", f"mode must be one of {MODES}")
    if path not in PATHS:
        raise DhError("BAD_PATH", f"path must be one of {PATHS}")
    root = Path(root)
    existing = load(root, required=False)
    if existing:
        return {"created": False, **summary(root, existing)}
    s = {"version": 2, "name": name, "mode": mode, "path": path, "created": now(),
         "phases": {p["id"]: {"status": "pending"} for p in PHASES},
         "gates": {g: {"status": "pending"} for g in GATES}}
    root.mkdir(parents=True, exist_ok=True)
    save(root, s)
    pending = root / "PENDING.md"
    if not pending.exists():
        pending.write_text((SKILL / "templates" / "PENDING.md").read_text(encoding="utf-8").replace("{{NAME}}", name), encoding="utf-8")
    log(root, {"event": "init", "mode": mode, "path": path})
    return {"created": True, **summary(root, s)}


def current(s: dict):
    """First phase that is neither done nor skipped (operate is the steady state)."""
    for p in PHASES:
        st = s["phases"][p["id"]]["status"]
        if st not in ("done", "skipped"):
            return p
    return PHASES[-1]


def blocking_gate(s: dict):
    """A gate owed by a finished phase that still blocks progress (phased mode only)."""
    if s.get("mode") != "phased":
        return None
    for p in PHASES:
        g = p.get("gate")
        if g and s["phases"][p["id"]]["status"] in ("done", "skipped") and s["gates"][g]["status"] != "passed":
            if p.get("optional") and s["phases"][p["id"]]["status"] == "skipped":
                continue
            return g
    return None


def summary(root: Path, s: dict) -> dict:
    cur = current(s)
    return {"project": str(root), "name": s["name"], "mode": s["mode"], "path": s["path"], "phase": cur["id"],
            "done": [k for k, v in s["phases"].items() if v["status"] == "done"],
            "gate": blocking_gate(s)}


def phase_done(root: Path, phase: str, evidence: dict | None = None, force_reason: str | None = None) -> dict:
    """Mark a phase done — only after its check passes (checks live in dhlib.checks)."""
    from . import checks
    s = load(root)
    if phase not in PHASE_IDS:
        raise DhError("BAD_PHASE", f"phase must be one of {PHASE_IDS}")
    idx = PHASE_IDS.index(phase)
    for prev in PHASE_IDS[:idx]:
        if s["phases"][prev]["status"] not in ("done", "skipped") and prev != "operate":
            raise DhError("OUT_OF_ORDER", f"phase '{prev}' is not done yet (`dh next` says what is)")
    g = blocking_gate(s)
    if g and PHASE_IDS.index([p for p in PHASES if p.get("gate") == g][0]["id"]) < idx:
        raise DhError("GATE_BLOCKED", f"gate {g} ({GATES[g]}) needs the owner's go: `dh gate pass {g}`")
    result = checks.run(phase, Path(root), s)
    if not result["ok"] and not force_reason:
        return {"ok": False, "phase": phase, "check": result}
    s["phases"][phase] = {"status": "done", "at": now(), "check": result, **({"forced": force_reason} if not result["ok"] else {}),
                          **({"evidence": evidence} if evidence else {})}
    p = PHASES[idx]
    if p.get("gate") and s["mode"] == "auto":
        s["gates"][p["gate"]] = {"status": "passed", "at": now(), "by": "auto"}
    save(root, s)
    log(root, {"event": "phase_done", "phase": phase, "ok": result["ok"], "forced": force_reason})
    return {"ok": True, "phase": phase, "check": result, **summary(root, s)}


def phase_skip(root: Path, phase: str, reason: str) -> dict:
    s = load(root)
    if not reason:
        raise DhError("NEED_REASON", "a skipped phase needs --reason (it is shown to the owner)")
    s["phases"][phase] = {"status": "skipped", "at": now(), "reason": reason}
    p = PHASES[PHASE_IDS.index(phase)]
    if p.get("gate") and (s["mode"] == "auto" or p.get("optional")):
        s["gates"][p["gate"]] = {"status": "passed", "at": now(), "by": "skip"}
    save(root, s)
    log(root, {"event": "phase_skip", "phase": phase, "reason": reason})
    return summary(root, s)


def gate_pass(root: Path, gate: str, note: str = "") -> dict:
    s = load(root)
    if gate not in GATES:
        raise DhError("BAD_GATE", f"gate must be one of {list(GATES)}")
    s["gates"][gate] = {"status": "passed", "at": now(), "by": "owner", "note": note}
    save(root, s)
    log(root, {"event": "gate", "gate": gate, "note": note})
    return summary(root, s)


def reopen(root: Path, phase: str, reason: str) -> dict:
    """Owner wants changes: reopen a phase (and everything after it)."""
    s = load(root)
    idx = PHASE_IDS.index(phase)
    for pid in PHASE_IDS[idx:]:
        s["phases"][pid] = {"status": "pending", "reopened": reason}
    for p in PHASES[idx:]:
        if p.get("gate"):
            s["gates"][p["gate"]] = {"status": "pending"}
    save(root, s)
    log(root, {"event": "reopen", "phase": phase, "reason": reason})
    return summary(root, s)
