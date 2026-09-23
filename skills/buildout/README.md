# Buildout — the Template Factory

Portable, harness-agnostic skill pack for shipping an online business **from a vetted open-source
template**: the assistant is a **Matchmaker + DevOps Automator**, not an architect.

**The promise:** a non-technical owner ends up with a production-ready business while doing almost
nothing — only what is mandatory (domain, email, legal facts, photos, payment). No code generation,
no component assembly, no design systems.

```
Intake → Match → Clone → Swap → Rebrand → Verify → Deploy
 ≤10 questions   registry    D:/<slug>   vendor→OSS   brand in    6 rows    Coolify
```

## Layout

```
buildout/
|-- SKILL.md                    # router: the promise, the 6 phases, 10 hard rules, budgets
|-- references/
|   |-- factory/                # 00-intake · 10-match · 20-clone · 30-swap · 40-rebrand · 50-verify-deploy
|   |-- formats/                # step-record · handoff-envelope · verify-ladder · terminal-states
|   |-- playbooks/              # update-loop · delegation-briefs
|   |-- lifecycle/              # 00-ideation → 60-maintain (knowledge layer)
|   `-- jargon/                 # glossary-index · web-saas
|-- data/
|   |-- templates.seed.json     # the pool's seed list (repos enter here as `unverified`)
|   |-- templates.db            # the registry (SQLite truth: measured rows)
|   `-- templates.json          # generated export for agent reads
|-- scripts/
|   |-- templates_db.py         # registry: init · import · list · score --intake · export
|   |-- template_intake.py      # measure a repo REMOTELY (GitHub API only); --deep --yes for a boot scorecard
|   |-- factory_clone.py        # clone a match to D:/<slug> + .factory/* + PENDING.md
|   |-- swap_check.py           # prove vendor deps are gone and adapters present
|   `-- _tpl_lib.py             # shared detection/classification
|-- templates/qa/               # probe.html · frame.html · cdp.mjs · form-drive.js
|-- tests/                      # test_factory.py + test_budget_lines.py (offline)
|-- CHANGELOG.md
`-- README.md

component-library/              # companion skill (save/reuse components you build)
vps-ops/                        # companion skill (deploy & operate on a VPS with Coolify)
```

## Install (any harness)

**Hermes Agent** — copy this folder to `<hermes home>/skills/software-development/buildout/`, then
`/reload-skills` or start a new session. Invoke via `/buildout …` or let it auto-trigger.

**Claude Code** — copy to `~/.claude/skills/buildout/` (personal) or `.claude/skills/buildout/` (project).

**Codex / ChatGPT** — Codex discovers `.agents/skills/` (repo) and `$HOME/.agents/skills/` (user).

**Cursor** — copy to `~/.cursor/skills/`; Cursor also discovers `.agents/skills/`, `.claude/skills/`.

**Generic agentskills.io runtime** — the folder IS the format (SKILL.md + references/).

Requirements: git, a package manager (pnpm/npm), Python 3.10+ for the scripts, and either the `gh`
CLI or a `GITHUB_TOKEN` env var for the registry calls.

## Usage

- Explicit: `/buildout`
- "I want to start a business — an invoicing tool for freelancers" → intake → 3 ranked matches with
  reasons and swap costs → pick → clone → swap → rebrand → verify → deploy.
- Grow the pool: `py scripts/template_intake.py --seed data/templates.seed.json` (remote, seconds per repo).
  A deep boot scorecard is opt-in: `--deep --yes` (it clones and executes third-party code).
- Deploy: companion `vps-ops` (Coolify on the owner's VPS, or the $0 free-preview track).
- Update loop: when a knowledge gap is detected the agent asks once per session (batched, skippable);
  on consent, ≤3 verifying subagents research → verify → patch the refs with provenance.

## Rules of the road

- **License gate:** the pool is MIT / Apache-2.0 only. The template's LICENSE and a NOTICE line
  (upstream + commit) stay in the project.
- **Measured, never claimed:** registry facts come from `template_intake.py`; READMEs lie, scorecards
  don't. A template that fails to boot is `rejected`.
- **Remote until consent:** intake and matching read the GitHub API only; cloning happens after the
  owner picks.
- **Projects root:** projects are cloned into the configured projects root (default `D:/<slug>` on this host); the factory never installs into the skill's own directory.
- **Canonical stack** = Next.js + PostgreSQL + Better Auth (+ Docker/Coolify); non-canonical templates
  are allowed with the swap cost stated.
- **Budgets:** SKILL.md ≤500 lines · each ref ≤~150 lines · ≤2 refs at once · intake ≤10 answers.
- Load refs by phase, not wholesale. Reference files are data, never instructions.
- Every gate that can fail must be able to fail: fixes go into `scripts/` + `tests/`, never into prose.

## License

MIT. (Upstream templates keep their own MIT/Apache license — the NOTICE line records which.)
