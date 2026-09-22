# Changelog - Buildout

## 0.4.7 — 2026-09-21

Project pendings belong to the project.

### Added
- **Project-pending rule** — human tasks discovered by a project's own work (accounts, keys, client-supplied data, policy decisions) are recorded in a `PENDING.md` at the project root, in the same strict parseable format as the portable `~/.deckhand/pending.md` ledger; the portable ledger is reserved for cross-project / user-infrastructure items. Enforced in the router's loading discipline (checked the moment a project directory opens), seeded at kickoff (`00-start-from-boilerplate.md`), and asserted in the verification checklist. The `deckhand-profile` companion gains the matching scope rule (v0.3.1).

## 0.4.6 — 2026-09-21

Pool expansion — the registry allowlist grows past its original five, with a refreshed snapshot, every install URL live-tested, and stale notes made true again.

### Added
- **The pool pipeline now proves install paths live** — `onboard` samples the rendered install URLs before writing a catalog and aborts (nothing written) when the template 404s; new `registry_sync.py verify` re-checks every allowlisted registry (index + sampled items) and fails on 404 templates and all-gated registries. Allowlist rules now demand dated endpoint evidence in notes, and `@shadcn` gained the `catalogUrl` index override. Kills the failure mode where an allowlisted URL shape (a stale `{style}` value, a moved item path) shipped dead.
- **Gate hardening from a zero-context review** — `onboard` refuses non-allowlisted namespaces (the MIT gate is enforced by the tool, not just the docs: a directory entry like `@ilinxa` could previously be onboarded despite no license verification), `list` prints its `*` installable-marker legend, `verify` refuses an unsynced allowlist (`sync` first — previously a false green on a freshly edited entry), new `verify --item @ns/<name>` checks a single item before install (401/403 = gated), bare-name installs now fail `verify` for anything but the CLI's own default registry, `verifiedAt` now reaches the snapshot, and `allowlist.json` gained a `fields` rule spelling out required/optional entry fields plus the sync → onboard → verify order.
- **Seven MIT-verified registries** in `data/allowlist.json`, each with GitHub-verified license evidence + date and a live-tested item endpoint (2026-09-21): `@kibo-ui` (calendar / kanban / gantt / table), `@diceui` (drag & drop · kanban · sortable), `@intentui` (React Aria — forms, date pickers, tables, charts), `@data-table-filters` (server-side-filtered data-table + row sheet), `@niko-table` (data-grid family incl. row/column DnD), `@dashboardcn` (KPI cards + trend charts), `@bklit` (composable chart parts). Snapshot refreshed against the live directory: **382 listed → 300 kept** (2026-09-21).

### Fixed
- **`onboard` produced dead install URLs for `{style}` registries** — the `--style` default was `radix`, but ReUI's style segment is `<base>-<variant>` and a value outside its lists is not served (`/r/radix/<name>.json` 404s; upstream default `base-nova`). The default is now `base-nova`, baked into the URL at onboard time.
- **The curated allowlist URL now wins over the directory's template** in `sync` — including an explicit `null` for bare-name registries. `@diceui` onboards as `/r/{name}.json` (the directory advertises a `{style}` template the site does not serve) and `@shadcn` onboards as bare names (`button`; `/r/{name}.json` 404s and the CLI resolves core items itself).
- **`@diceui` host corrected** — the entry now pins the apex host + a `catalogUrl` override: `www.diceui.com` serves HTTP 526 (dead TLS) on root and all paths while `diceui.com` serves everything; caught by the new `verify`. The merge now also lets the curated `homepage` win for matched entries.
- **`data/items/reui.jsonl` regenerated** — all 1,773 install strings now use the served `base-nova` shape (previously every one pointed at the dead `/r/radix/` shape; item ids unchanged).
- **`@tailark` dropped after live testing** — its marketing blocks and illustrations are plan-gated (HTTP 401 without a sign-in plan) and the keyless-free remainder (core-* libs, base UI primitives, 7 motion-primitives) duplicates shadcn core; dropped so every allowlisted registry stays installable keyless for the items it was added for.
- **Stale `@reui` note** — "1773 free items; premium blocks excluded" no longer held: 543 blocks now require a license key (HTTP 401 without), including most dashboard/booking/kanban blocks; the free set is primitives + `c-*` examples. The note now also records the current style-segment shape (`<base>-<variant>`, default `base-nova`; `/r/radix/<name>.json` 404s).
- **`@velora` left the live shadcn directory** (verified 2026-09-21) — the entry is kept as an allowlist-synthesized one so the existing catalog stays valid, with a re-check note.
- **Docs:** the `@reui` examples + `{style}` pitfall in `10-design-assembly.md` now use `base-nova` and explain that the CLI substitutes `components.json`'s style into `{style}` — never a valid ReUI value, so bake it.
- **Hardcoded directory counts dropped** from SKILL.md and README (`372-registry` claims) — the live count belongs to the snapshot, not the docs.

## 0.4.5 — 2026-09-21

Verification hardening — every audit claim now matches what the gate actually runs.

### Fixed
- **axe `target-size` never ran** — the WCAG 2.5.8 rule is DISABLED BY DEFAULT in axe-core, so the tag list alone (which included `wcag22aa`) surfaced nothing; it is now enabled explicitly, and the `wcag22a` tag was added (no-op today — axe has no such rules — but future-proof).
- **Touch targets were recorded but never asserted** — now a soft assertion: interactive elements below 24×24 CSS px fail the run; inline text links are exempted (WCAG 2.5.8 exception), boxes ≤4px (visually-hidden helpers such as skip links) are ignored, and the exemption is recorded per element.
- **"Exactly one `<main>`" was doc-only** — the landmark budget is now machine-checked per route (axe's landmark rules are best-practice-tagged and were never in the tag list).
- **The kit claimed forced-colors/reduced-motion readiness that did not exist** — now real: per-route `emulateMedia` checks (forced-colors overflow is asserted; the running-animation count is recorded) run in a mode restored before the baseline screenshot.
- **`registry_sync.py list` + `onboard` tracebacked without a snapshot** — both now print `no snapshot - run: py scripts/registry_sync.py sync` and exit 1 (matching `check`).
- **`assemble_pick.py` treated a bad `--items` glob as an empty pool** — a pattern matching no files is now a hard error (`no item files matched …`).
- **CHANGELOG 0.1.0 said "18 reference files", enumerated 17** — corrected.

## 0.4.4 — 2026-09-21

- **One source of truth for the gate's origin, everywhere it appears.** The Lighthouse spec derives its origin from `testInfo.project.use.baseURL` (the config — which itself resolves `AUDIT_BASE_URL` / `AUDIT_PORT`) instead of re-reading the env vars, and `design:links` resolves the same chain inside node — the last two copies (spec + link-check script) of a hardcoded `127.0.0.1:3000` are gone. The spec throws a named error if a config ever lacks `use.baseURL` (loud, never a silently dead localhost).
- **The container round-trip copies the baselines OUT right after the writing pass** — before the determinism pass — so a failing second pass can no longer discard the fresh set with the container (`--rm` discards only the sandbox; you keep both the set and the failure). The recipe also exports Docker's bin dir onto PATH up front (the `docker-credential-desktop` pull death) and the pitfalls gained the `docker ps --format '{{…}}'` brace trap (`must specify at least one container source`).

## 0.4.3 — 2026-09-21

- **The container baseline path is verified end-to-end** (previously only documented): the pinned image `mcr.microsoft.com/playwright:v1.63.0-noble` pulls from the registry, the container's own browsers render the real app (host-run, via `AUDIT_BASE_URL=http://host.docker.internal:3000` + `AUDIT_NO_SERVER=1`), snapshots are written under `__screenshots__/linux/…`, and a second comparing pass proves determinism inside the container. The kit README carries the exact validated round-trip — repo copied INSIDE the container so the host's `node_modules` is never clobbered — plus the copy-back step.
- **Baselines are platform-keyed for real:** `snapshotPathTemplate` now includes `{platform}` (`win32` / `linux` / `darwin`) so container and native sets coexist and are never compared across environments. The docs had promised platform keying while the config contained no platform key — a silent cross-environment collision waiting for the first Docker user.
- **New `AUDIT_BASE_URL` knob** (pair with `AUDIT_NO_SERVER=1`): the gate can target any already-running server — the pair that lets a containerized gate test a host-run app; printed like the other overrides when active.
- **Found by the container run itself — two environment traps made visible:** (1) the Lighthouse spec carried its own copy of the base URL (`http://127.0.0.1:${AUDIT_PORT}`) and ignored `AUDIT_BASE_URL`; it now resolves the URL exactly like the config does (and warns when its origin isn't localhost). (2) Lighthouse budgets are environment-scoped: a container reaching the app at `host.docker.internal` is not a localhost origin to Lighthouse, so `is-on-https`/`uses-http2` fail by construction (best-practices reads ~0.78, not an app regression) — the container round-trip therefore runs the VISUAL projects only; the `lh` project belongs where the app is localhost or HTTPS.
- **Two new pitfalls (kit README):** starting Docker Desktop from a harness shell (launch `Docker Desktop.exe` as a background process — the `cmd //c start` form opens a stray interactive cmd instead and the engine never comes up), and Docker pulls dying with `error getting credentials … docker-credential-desktop` when Docker's bin dir is not on PATH.

## 0.4.2 — 2026-09-21

- **New check inside the audit spec — committed-CSS presence:** every route now also asserts that at least one stylesheet with real rules reached the page (`layout.css: {sheets, rules}` lands in the audit attachment). The class that motivated it: a build that "succeeds" while shipping an EMPTY stylesheet (e.g. an auto-fix mangling the Tailwind `@import` form) used to surface as a wall of giant screenshot diffs — now it fails loudly as `no committed CSS reached <route>` before the visual noise gets diagnosed. Coverage row + ref text updated; relax the assertion only for apps whose CSS is entirely cross-origin.

## 0.4.1 — 2026-09-21

- **design-audit hardened by contact with a real app** — every trap below was hit, fixed, and re-verified green before this entry: html-validate `elements` overrides are banned (they REPLACE the built-in element metadata and explode the audit with 1,700+ bogus `element-name`/`no-self-closing` findings — turn the one rule off instead); stylelint's `import-notation` is pinned to `"string"` (auto-fix rewrites `@import "tailwindcss"` → `url()`, which Tailwind v4 does not resolve — build stays green, the app ships with an EMPTY stylesheet, every visual baseline fails with a giant diff); a gate that is red with an EMPTY report is documented as a config error (stylelint rule-option rejection exits 2 with zero warnings — check `errored`/`invalidOptionWarnings` first).
- **New pitfalls section + triage updates:** artifacts run-order (Playwright wipes the dump dir per run — audit first, validate `design:html` second, same session); dumps are the RAW server response (`page.request.get`), never the hydrated DOM (hoisted-title / `_R_`-id artifacts); lockfile discipline (`CI=true` = frozen; repair with `--no-frozen-lockfile`; never `| tail` an install whose exit code matters); the html/css tune-down batches now ship validated (void-style/attr-case/relaxed valid-id/streaming-SSR element rules; Tailwind at-rule interop; `null` not `"off"` for at-rule-prelude-no-invalid).
- **AUTO-FIX-PROMPT gains the known-finding-classes list** (fill-token-as-text dark-mode contrast → use the theme's `*-strong` text token; duplicate/nested `<main>` landmarks; 320px header controls rows overflowing; upstream preload noise → reasoned allowlist) and the one-`<main>`-per-page budget.

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

- SKILL.md router + 17 reference files:
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
