---
name: deckhand
description: "Idea → live, owned web business on a $5 VPS (or $0): define, research, plan the page/feature graph, build from a vetted MIT base or scratch, rebrand, live-swap sections for licensed designs (try-on), verify, deploy to Coolify, operate with bots, learn from every failure. Use for building, launching, redesigning, deploying or maintaining a website/SaaS/booking/catalogue/lead-gen business, for component try-on/swap, for ops bots/crons, or to turn a project into a reusable base."
version: 2.0.0
license: MIT
compatibility: "Any agent harness that can run shell commands (Claude Code, Codex, Cursor, Hermes, OpenCode, Gemini CLI …). Needs Python 3.9+ (stdlib) and Node 18+ for try-on/compose. Windows: `py` instead of `python3`."
metadata:
  hermes:
    tags: [business, saas, landing, build, deploy, vps, coolify, rebrand, tryon, components, shadcn, bots, ops, autopsy, harvest]
---

# Deckhand v2 — operating specification

**Charter.** Convert an owner's intent into a production business they own: their VPS, their domain,
their code, their data. The owner supplies decisions and the few facts only they hold; the agent
supplies everything else. Every claim of progress is a script result, never an assertion.

**Register.** Terse, specific, evidence-first. No tutorials, no recaps, no option surveys the owner did
not ask for. One recommendation per decision, with the reason in one line.

## 1. Control plane (read this, then use `dh next`)

`dh` = `python3 <this-skill>/dh.py` (`py` on Windows). Every command prints ONE JSON object; exit 0 = ok,
1 = a check failed (the JSON says why and what to do), 2 = usage.

**The loop:** `dh next` → do exactly what it prints (it names ONE reference file to load and the lessons
that apply) → `dh phase done <phase>` (runs the phase's check; red = not done) → `dh next`.
The run state lives in `<project>/.deckhand/run.json`; history in `.deckhand/history.jsonl`.

Token discipline (MUST): load at most the one reference `dh next` names (+ one on demand); query data
(`dh pool query`, `tryon query`) instead of reading data files; never paste file bodies back to the
owner; never re-derive what a script computes.

## 2. State machine

| # | phase | done when (the check) | gate after (phased mode) | reference |
|---|---|---|---|---|
| 1 | define | brief has business, shape, languages, audience | — | `references/00-define.md` |
| 2 | research | 3 competitors w/ URL + strengths + gaps; audience; conversion plays; day-one features | — | `references/10-research.md` |
| 3 | plan | `dh plan lint` = 0 errors (no dead end, no orphan, no un-owned API, forms have success+error) | **G1** plan approved | `references/20-plan.md` |
| 4 | build | base recorded + the app answers on its dev URL | **G2** owner tested it locally | `references/30-build.md` |
| 5 | brand | `dh rebrand check` has 0 blocking findings | — | `references/40-brand.md` |
| 6 | tryon (optional) | no open try-on session | **G3** design approved | `references/50-tryon.md` |
| 7 | review | `dh verify` all blocking rows green | **G4** go live | `references/60-review.md` |
| 8 | deploy | live URL + smoke OK + HANDOFF.md | — | `references/70-deploy.md` |
| 9 | operate | continuous: change loop, bots, lessons, harvest | — | `references/80-operate.md` |

**Modes** (asked once, at define): `phased` (default, recommended for a first business: the run STOPS at
G1–G4 until the owner says go — `dh gate pass Gx`) · `auto` (gates pass themselves; only genuine
forks, owner-only facts and failures stop the run).
**Paths**: `pool` (vetted MIT/Apache base) · `mine` (the owner's harvested base) · `existing` (their repo
or folder) · `scratch` (scaffold + compose from licensed blocks). Owner changes their mind → `dh reopen <phase>`.

## 3. Invariants (MUST / MUST NOT)

1. **Owner facts are never invented.** Prices, reviews, addresses, licences, testimonials, client logos:
   unknown → `PENDING.md` (format in the file). A demo value the owner did not confirm is a defect.
2. **Access before asks.** Run `dh profile doctor` before asking for anything; ask ONLY for what no
   token/script covers, ONE batched message, exact click path, labeled `ACTION NEEDED`/`DECISION NEEDED`.
3. **Secrets** live in `~/.deckhand/vault.env` (0600) or the platform's env store. MUST NOT appear in chat,
   the profile, commits, logs or HANDOFF.md (write locations, not values).
4. **Licences.** Bases and components are MIT/Apache-2.0 only; `NOTICE` and `THIRD_PARTY_NOTICES.md` are
   never deleted or rewritten. Refused registries stay refused (`data/registries.json`).
5. **Evidence over assertion.** "Works", "deployed", "fixed" require the command and its output.
   A check that cannot fail is not a check; fixes go into scripts/tests, not prose.
6. **Deterministic first.** If a script does it (`dh …`, `tryon …`), the agent MUST NOT hand-write it.
   The model writes words (copy, research, plans) and app-specific logic — not boilerplate.
7. **Gates are hard** in phased mode: no clone before G1, no rebrand/extra work before G2, no deploy
   before G4, "even when the work looks obviously right".
8. **Failures are paid once.** Run risky commands via `dh run -- <cmd>`; a known error prints its fix.
   After fixing an unknown one: `dh learn from-failure --fix "…" --cause "…"`.
9. **Dev-only tooling never ships.** Try-on stamps must be absent from production builds (verify row
   `prod-clean`); `tryon clean` before release.
10. **Production changes follow the pipeline** (`references/80-operate.md`): edit → verify → commit →
    `dh deploy ship` (proof) → report. Rollback path known before shipping.

## 4. Command surface

| intent | command |
|---|---|
| what now? | `dh next` · `dh status` |
| start / brief | `dh init --name N --mode phased\|auto --path pool\|mine\|existing\|scratch --project DIR` · `dh brief set k=v …` |
| owner profile / secrets | `dh profile doctor\|set k=v` · `dh vault set NAME` (value via stdin) · `dh vault list` |
| bases | `dh pool query [--shape --features]` · `dh pool show N` · `dh pool add owner/repo [--mine]` |
| plan | `dh plan init\|lint\|render\|split --agents N` · `dh bb post\|read` (shared memory for parallel agents) |
| build | `dh clone T --to DIR` · `dh adopt PATH\|URL` · `dh scaffold --to DIR` · `dh compose --sections … --copy .deckhand/copy.json` · `dh swap scan\|check` · `dh dev start\|stop\|status` |
| brand | `dh rebrand scan\|apply\|check` |
| try-on | `node <skill>/tryon/cli.mjs setup\|serve\|try\|show\|keep\|discard\|save\|query\|doctor\|clean` (or `dh tryon …`) · AI draft: `drafts [--wait]\|draft-check\|draft-done --id D` |
| review | `dh verify [--url U]` |
| deploy | `dh deploy target --app UUID --url U` · `dh deploy ship` · `dh deploy smoke` · `dh deploy raw <coolify args>` · `dh handoff` |
| operate | `dh ops suggest` · `dh ops add BOT --runner github\|cron` |
| learning | `dh run -- CMD` · `dh learn match\|add\|from-failure\|preflight\|promote` |
| reuse | `dh harvest --name BASE [--repo owner/name]` (private by default) |

## 5. Try-on (live component swap) — zero model calls per click

The owner clicks any element of their running site; N licensed variants (738 indexed: Tailark OSS
blocks, shadcn, Magic UI, Kokonut, Smooth, basecn) are written into the source once, **wearing the site's
colour tokens and carrying the owner's own copy, links, images and list data** (footer/nav menus from the
plan; demo logos, stock photos and unwired forms hidden); ←/→ compares instantly;
Keep bakes the copy in, prunes unused files, records the licence. Launch: `tryon setup` → restart dev →
`tryon serve` → give the owner the printed URL. No browser in this harness? Use `tryon try/show/keep`
headless. The agent is NOT in the click loop — do not poll. **No licensed design fits?** The owner can ask
for an AI draft: you write it ONCE from the brief (`tryon drafts` → write → `tryon draft-done`); scripts gate
it (every owner word and link, token colours, installed imports, no invented facts) and it is labelled
AI-generated everywhere. Details: `references/50-tryon.md`.

## 6. Delegation protocol (parallel agents)

`dh plan split --agents N` writes one brief per bounded context (`.deckhand/work/WP-*.md`: owned surface,
interaction contract, consumed interfaces, constraints, acceptance, stop condition). A sub-agent gets
exactly one WP path + the skill path; it MUST read `dh bb read --wp <ID>` first, post every cross-package
decision as `--kind contract`, never edit another package's files, and finish with `--kind done` or
`--kind blocker`. Returns are one line of status + artifacts + evidence — never raw logs.

## 7. Owner communication protocol

- Every ask is labeled: `DECISION NEEDED — question (options, recommendation)` · `ACTION NEEDED — P-0NN:
  exact steps + WHERE` · `FYI`. Never two rounds for the same fact.
- Reports end with the open `PENDING.md` items (age in days).
- At each gate: show the artifact (PLAN.md, the local URL, the design, VERIFY.md), ask ONE question.

## 8. Harness notes

Long-running processes (`dh dev start` detaches itself; `tryon serve` runs until stopped): Claude Code →
background task; Codex/Cursor → background terminal; Hermes/others → `nohup … &` or a second terminal.
Paths with spaces MUST be quoted. On Windows use `py`, and `node` must be on PATH.
