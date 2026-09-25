"""`dh next` — ONE instruction for the current state: what to run, which single reference to load,
the lessons that apply, and what makes the phase done. The agent never re-reads the whole skill."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from .util import SKILL, read_json
from . import state as STATE
from . import learn as LEARN

DH = f'{"py" if os.name == "nt" else "python3"} "{SKILL / "dh.py"}"'
TRYON = f'node "{SKILL / "tryon" / "cli.mjs"}"'

STEPS = {
    "define": ["{dh} profile doctor            # what access exists (never ask for what a token already covers)",
               "{dh} brief set business=\"…\" shape=saas|booking|catalogue|marketplace|leadgen|internal languages=en,… audience=\"…\" brand.name=\"…\"",
               "ask ONLY what the brief + profile cannot answer — one batched message, defaults proposed",
               "{dh} phase done define"],
    "research": ["research the market on the web: 3 real competitors (URL, positioning, pricing, strengths, gaps), audience, conversion plays, day-one features",
                 "write .deckhand/research.json (template: {skill}/templates/research.json) — every claim has its URL; unknown = unproven[]",
                 "{dh} phase done research            # or: {dh} phase skip research --reason \"owner declined\""],
    "plan": ["{dh} pool query                     # path=pool/mine: top 3 bases for this brief (reasons + gaps)",
             "write .deckhand/sitemap.json: every page, section, action and its target, every form's success+error (template in .deckhand/ after `{dh} plan init`)",
             "{dh} plan lint                      # until 0 errors — no dead ends, no orphan pages, no un-owned API",
             "{dh} plan render && {dh} plan split --agents 3   # PLAN.md for the owner; work packages for parallel agents",
             "{dh} phase done plan  → show .deckhand/PLAN.md + the chosen base; wait for the owner's go (G1)"],
    "build": ["path=pool|mine: {dh} clone <template> --to <projects_root>/<slug>",
              "path=existing: {dh} adopt <folder|git-url>     path=scratch: {dh} scaffold --to <dir> && {dh} compose --sections hero,features,pricing,faq,cta,footer --copy .deckhand/copy.json",
              "implement the work packages (.deckhand/work/WP-*.md); agents coordinate ONLY via `{dh} bb post|read`",
              "{dh} dev start                      # prints the local URL for the owner",
              "{dh} phase done build  → give the owner the URL; wait for their go (G2)"],
    "brand": ["{dh} rebrand scan && {dh} rebrand apply     # brand from the brief: name, tagline, primary colour, icon",
              "{dh} rebrand check                  # template names, demo copy, fake logos, placeholders",
              "{dh} phase done brand"],
    "tryon": ["{tryon} setup --project . && restart the dev server",
              "{tryon} serve --project .           # the owner opens that URL, clicks Try-on, compares, keeps",
              "no browser? {tryon} try --file <f> --line <n> --col <c> --slot hero   then show / keep / discard",
              "AI draft asked (overlay, serve's draft_request line, or the owner says so): {tryon} drafts → write the brief's component into write_to → run its `then` (gated; labelled AI-generated)",
              "{dh} phase done tryon  (or skip it) → wait for the owner's go on the design (G3)"],
    "review": ["{tryon} clean --project .          # unwire try-on (kept sections stay)",
               "{dh} verify                         # builds, serves the build, checks every row; red rows are fixed, not argued with",
               "{dh} phase done review  → owner says go live (G4)"],
    "deploy": ["first time: references/ops/00-user-checklist.md → 10/11 (server) → 20/21 (domain) → 30 (app); then {dh} deploy target --app <uuid> --url https://…",
               "{dh} deploy ship                    # push → deploy → wait for YOUR commit → smoke",
               "{dh} handoff                        # HANDOFF.md: access locations, commands, pending",
               "{dh} phase done deploy"],
    "operate": ["change requests: edit → {dh} verify → commit → {dh} deploy ship (references/80-operate.md)",
                "{dh} ops suggest → {dh} ops add <bot> --runner github|cron   (verify each schedule by its own trigger)",
                "a failure fixed? {dh} learn from-failure --fix \"…\" --cause \"…\"    ·   liked the result? {dh} harvest --name <base>"],
}


def next_step(root: Path) -> dict:
    root = Path(root)
    s = STATE.load(root, required=False)
    if not s:
        return {"state": "no run", "do": [f"{DH} init --name <business> --mode phased|auto --path pool|mine|existing|scratch --project <dir>"],
                "read": str(SKILL / "references" / "00-define.md"), "dh": DH}
    gate = STATE.blocking_gate(s)
    cur = STATE.current(s)
    if gate:
        return {"state": "waiting for the owner", "gate": gate, "what": STATE.GATES[gate],
                "do": [f"show the owner what {gate} is about; on their go: {DH} gate pass {gate} --note \"…\"",
                       f"changes requested instead: {DH} reopen <phase> --reason \"…\""], "dh": DH}
    steps = [x.format(dh=DH, tryon=TRYON, skill=SKILL) for x in STEPS[cur["id"]]]
    out = {"phase": cur["id"], "n": f"{STATE.PHASE_IDS.index(cur['id']) + 1}/{len(STATE.PHASES)}", "title": cur["title"],
           "mode": s["mode"], "path": s["path"], "read": str(SKILL / cur["ref"]), "do": steps,
           "lessons": LEARN.preflight(root, cur["id"]), "dh": DH}
    if cur["id"] == "plan":
        brief = read_json(root / ".deckhand" / "brief.json", {}) or {}
        if s["path"] in ("pool", "mine") and brief:
            from . import pool as POOL
            q = POOL.query({**brief, "lane": brief.get("lane", "web")})
            out["pool_top"] = [{"name": t["name"], "score": t["score"], "reasons": t["reasons"][:4]} for t in q["top"]]
            if q["gap"]:
                out["pool_gap"] = "nothing in the pool fits — offer path=scratch (scaffold + compose) or measure more repos (dh pool add owner/repo)"
    return out
