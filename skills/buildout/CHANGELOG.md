# Changelog - Buildout

## 0.4.0 — 2026-09-21

- **New: the design-audit gate** (ref `30-design-audit.md` + `templates/design-audit/`) — one command covers the whole front-end surface: visual baselines per project (desktop/mobile/dark/WebKit), Firefox smoke, WCAG 2.2 A/AA (axe), console + page errors, failed & 4xx/5xx requests, horizontal overflow incl. a 320px reflow probe, touch targets, title/description/OG, Lighthouse perf/SEO/best-practices, link crawl, HTML validity, CSS + jsx-a11y lint — and emits ONE machine-readable report (CTRF spine; the agent reads only a one-line failure filter). No custom test framework: two thin spec files wire maintained OSS (Playwright 1.63 · axe-core 4.13 · Lighthouse 13.5 · linkinator · html-validate · stylelint/jsx-a11y; every pin registry-verified 2026-09-21).
- **Deterministic by construction:** baselines generate only in the pinned Playwright container (`mcr.microsoft.com/playwright:v1.63.0-noble`) and change only through explicit `design:audit:update` commits; a missing baseline fails instead of passing silently; degraded (no-Docker) mode documented — environments never mix.
- **Fix loop as data:** `AUTO-FIX-PROMPT.md` bans the classic cheats (editing snapshots, loosening thresholds, skipping real failures) and scopes re-runs with `--grep`.
- Verified end-to-end before shipping: a static-fixture dry run (6/6 green + Lighthouse pass), then a **fresh-eyes zero-context run on a real production app** — 28 tests executed, baselines deterministic across repeated runs — which caught **three kit blockers before release** (linkinator's `--verbosity error` produced an empty "passed" report; html-validate rejects `$comment` in its config schema and v11 has no `-o` flag) plus the traps around it (non-TTY `pnpm install`, ambient `AUDIT_*` inheritance, a `src/`-only CSS glob, a missing eslint config, build-dir noise flooding the lint report) — all fixed and re-verified before tagging.

## 0.3.3 - 2026-09-21

- **Local-build freshness pre-flight.** Born from a real run: a rebuild under a still-running local server left the old manifest serving, so the page answered 200 while a client-rendered feature never appeared — no console error, no server error, and three diagnostic probes went hunting for a bug in new code that was not there (the real cause: a restart that failed with `EADDRINUSE: address already in use`). Hard Rules now say: prove the server is serving the build you just made (kill by PID → 0 listeners → restart → freshness check); `verify-ladder.md` gains a **Freshness** section with the both-states command output, plus the Windows/MSYS `taskkill /F /PID` single-slash note.

## 0.3.2 - 2026-09-20

- Fresh-eyes audit fixes: script commands now state the working directory + `python3` on macOS/Linux (the companion `component-library` script lives in ITS dir — the old `py scripts/library.py` reads were a stall trap); "buildout engine (v0.2)" version labels dropped; store rename documented (`~/deckhand-library` / `DECKHAND_LIBRARY`, legacy env honored); trigger-eval phrase updated (`expert pack` → `buildout pack`); `OPS.md` marked as created by `vps-ops` ref 30.

## 0.3.1 - 2026-09-20

- **Deployed-app rule + checkpoints** (born from a real run: one hour of uncommitted edits, then the model stream was cut mid-turn — nothing shippable). Loading discipline now states: read BOTH portable files **before starting work**; a project dir containing `OPS.md`/`.vps-ops.json` is a LIVE app → `vps-ops` change pipeline, and done = committed → pushed → deployed → smoke-passed, with a commit checkpoint at every milestone; wide requests ship in passes.
- Frontmatter version synced to 0.3.x (was stale at 0.2.2 while the changelog said 0.3.0 — again).

## 0.3.0 - 2026-09-19

Renamed `expert-build-pack` → **`buildout`** as part of the pack rebrand to **Deckhand** (invocation: `/buildout`). No content changes.

## 0.2.2 - 2026-09-18

- Cross-links to the `vps-ops` free-preview track (Oracle Always Free + free domain → later migration): buildout step 5 + routing row.
- Frontmatter `version` corrected (was stale at 0.2.0 while the changelog/README said 0.2.1).

## 0.2.1 - 2026-09-17

Cross-references to the new companion skill `vps-ops` (VPS deploy & management with Coolify). No functional changes.

- SKILL.md: buildout flow step 5 + routing row → `vps-ops` (bootstrap → Coolify → deploy → change pipeline → ops).
- `references/lifecycle/50-deploy.md` + `60-maintain.md`: execution pointers to `vps-ops`.

## 0.2.0 - 2026-09-17

Buildout engine: boilerplate start + coherent design assembly from the living shadcn registry pool + companion `component-library` skill.

- New data: `data/allowlist.json` (5 MIT-verified registries w/ evidence), `data/boilerplates.json` (open-saas, next-saas-starter, velora-ui — MIT verified 2026-09-17 via GitHub API), generated `data/registries.snapshot.json` (372 listed -> 282 kept) and `data/items/*.jsonl` catalogs (velora 64 - reui 1,773 - cult-ui 157 items).
- New scripts (stdlib Python): `scripts/registry_sync.py` (sync/check/list/onboard; includes --catalog-file offline path and a 403/429 UA fallback), `scripts/assemble_pick.py` (seeded deterministic picker; curated sections + text-match for uncurated catalogs).
- New refs: `references/buildout/00-start-from-boilerplate.md`, `10-design-assembly.md` (lock schema, anti-slop banlist, verify gates), `20-component-library.md`.
- Companion skill `component-library` v0.1.0 (store at ~/expert-build-library; index.jsonl + registry.json + r/<name>.json; add/find/list/show/copy/remove).
- Tests: 9 pack tests + 4 library tests green; picker determinism verified (identical hashes across runs); snapshot + data JSON validated.

### Notes

- cult-ui rate-limits its site (429 / Vercel checkpoint) from some IPs; onboard from the repo mirror `apps/www/public/r/registry.json` via `--catalog-file` (path recorded in the allowlist note).
- Registry Health is experimental upstream; the allowlist overrides filters for curated kits.

## 0.1.0 - 2026-09-17

Initial release.

- SKILL.md router + 18 reference files:
  - formats/: step-record, handoff-envelope, verify-ladder, terminal-states
  - playbooks/: update-loop, delegation-briefs
  - lifecycle/: 00-ideation, 10-foundations, 20-build, 30-design, 40-git, 50-deploy, 60-maintain
  - jargon/: glossary-index, web-saas
  - eval/: README, trigger-eval.json
- Source: Phase-1 research synthesis (8 parallel research streams, 97 dated sources, priority window 2026-08-18 -> 2026-09-17). Full evidence doc: "Harness Skill Pack - Phase 1: Research & Brainstorm" (2026-09-17).

### Measured rules embedded (key citations)

- Bounded-efficiency clause + waste blocklist - arXiv:2608.01347
- Typed retention + verbatim constraint pinning (compaction keeps 96% vs 10%) - arXiv:2608.22752, arXiv:2606.22528
- Handoff envelope fields / rediscovery savings (-20-59% events, -42-63% tokens) - arXiv:2606.02875
- Independent verification (producer/verifier separation, test-source fidelity) - arXiv:2609.09133, arXiv:2609.01481, arXiv:2609.09776
- Boundary prompting (+9.2% success) - ACL 2026 long paper (aclanthology 2026.acl-long.1711)
- Paired Skill Lift evaluation - NVIDIA SkillEvaluator (2026-08-19); ACES, arXiv:2608.20614
- Caution: skills can hurt (Pass@2 -1.3..-4.2%, tokens +72-394%) - arXiv:2608.23067
- Trigger-surface budgets & failure modes - OpenAI Codex skills docs; Claude Code issues #46952/#30387
- Update-loop safety - memory poisoning, arXiv:2609.13889; verification-status laundering; confirmation fatigue

## Open

- (none yet - verifier abstentions are recorded here per the update loop)
