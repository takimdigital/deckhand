# Changelog - Buildout

## 0.8.2 — 2026-09-23

### Fixed
- **A stale measurement can no longer roll the registry back.** Two intake runs on one registry were
  observed racing: both measured the same eight templates, and the slower one finished last, silently
  overwriting newer rows with older measurements. `upsert` now takes the run's start stamp
  (`not_before`) and refuses to overwrite a row updated after it — `template_intake.py` passes it and
  prints `SKIPPED` instead of pretending to write. Exercised against the live registry (stale write
  skipped, a template's real star count intact). Rule recorded in `references/factory/00-intake.md`:
  never run two intakes at once.
- `tests/test_factory.py` — 48 tests (was 47).

## 0.8.1 — 2026-09-23

The pool got a memory. Each template now carries a **measured detail file** — real routes, real
features, the env names it demands at build time, its deploy story, its rebrand surface, and the
traps that would cost an hour. One subagent per repo measures it through the GitHub API (no clone);
one command imports it. The registry became a place that answers *what is it like to work with this*,
not only *what does it declare*.

### Added
- **`references/pool-details.md` + `references/pool-details-contract.md`** — the fan-out procedure
  (one subagent per repo, remote-only, env vars by name) and the field-by-field schema.
- **`templates_db.py import-details <dir|file>`** — validates each file, refuses a missing
  `repo`/`slug`, a credential-shaped value, a repo that is not in the registry, and a file whose slug
  matches a row measuring a **different** repo (cross-attachment). Stores the blob, promotes
  `features`/`locales`/`swap_burden` into queryable columns, and ships `data/details/<slug>.json`.
- **`blocking[]`** — the only channel that can stop a template: `injected-payload` (shipped code
  carries an obfuscated blob) and `install-impossible` (a dependency that does not exist). Imported
  as an auditable `risk_flags` entry with `source: pool-details` and made a hard blocker.
- **Schema migration** — an older `templates.db` is brought forward column by column instead of
  crashing (`connect` now ALTER-ADDs what is missing).
- **Export digest** — the bulk `templates.json` carries a compact digest per row; the ~20 KB blobs
  stay in SQLite and in `data/details/`, read on demand.
- **Measured-cost scoring** — a detail file proving `db: none` now costs 25 points on an ask that
  must store data, and says so in the reasons.
- **`tests/test_factory.py`** — 47 tests (was 36): import validation, credential refusal,
  cross-attachment, blocker derivation, blocker survival across a re-measurement, prose-≠-blocker
  regression, migration, and the measured-cost scoring.

### Fixed
- **A phantom vendor in the pool.** `classify_deps` matched bare words inside other words and read
  the README as config: `ably` was recorded as a Next-Elite dependency because the README says
  "pro**bably**". Vendors now come from dependencies and config files only; a README name-drop is
  recorded separately (`vendor_name_in_readme_only`) and never becomes a swap.
- **Env-var names stopped matching.** The first word-boundary fix treated `_` as a word character, so
  `NEXT_PUBLIC_POSTHOG_KEY` no longer matched `posthog` and real vendor deps silently disappeared
  (proved by a pool-wide before/after diff). Plain-word patterns now match whole tokens, `_` splits.
- **Two healthy templates were temporarily mis-flagged** by a text-regex blocker rule ("no bun
  lockfile" while an npm lockfile exists; a passing mention of `npm ci`). Blockers are structured
  now — a regex over free text is not a measurement.
- `_promote` derives `swap_burden` from prose safely, and `upsert` merges instead of erasing the
  detail-derived flags on a re-measurement.

### Pool (8 repos, measured 2026-09-23)
Featuring the first honest ranking: for a French+Arabic invoicing ask, Next-Elite falls from #1 to #3
once its detail file proves it has **no database**, and the two poisoned repos are named as blocked —
`nextjs-saas-starter` (≈20 KB of obfuscated JS welded onto `postcss.config.mjs`) and
`Micro-SaaS-Starter-Kit` (`@radix-ui/react-skeleton` does not exist on npm).

## 0.8.0 — 2026-09-23

The Template Factory — a full rewrite of the creation logic, after the owner's verdict on the 0.7.0 runs: *"multiple ideas inside one that interfere … the result is crappy … the problem is the workflow … we over think interconnected things."* The pack no longer **generates** products; it **matches, clones, swaps and rebrands** them. Intake → Match → Clone → Swap → Rebrand → Verify — one idea per phase. 0.7.0 was never released; its composition layer is deleted (below), not deprecated.

### Added
- **`scripts/templates_db.py` — the registry** (SQLite truth + `data/templates.json` export): rows carry license/SPDX, stars, last push, stack, canonical flag, vendor deps, swap-map draft, boot scorecard, risk flags, rebrand surface. Deterministic scoring with published weights (shape +40 · features +10 each cap +30 · RTL +10/+4 · canonical +15 · boot +10/+5 · verified +5 · swap cost −2 each cap −10 · stale −20 · no-tests −5) and hard blockers (no license / archived / build failed → never ranked). `data/templates.seed.json` seeds the owner's first 8 repos.
- **`scripts/template_intake.py` — remote measurement.** Reads a repo through the GitHub API only: metadata, license, full file tree, key manifests, contributor concentration, README placeholders. **No clone, no disk, no execution.** `--deep --yes` (consent-gated) adds the one fact that cannot be read remotely: the boot scorecard (install/build/start, timed).
- **`scripts/factory_clone.py`** — clones a matched template into `D:/<slug>` (root configurable), drops upstream history (fresh `git init` + one commit naming the upstream commit), writes `.factory/{match,swap-map,brand,scorecard}` + `PENDING.md`, and refuses unlicensed rows or non-empty folders.
- **`scripts/swap_check.py`** — proves the swaps: vendor SDK absent outside declared `allow` globs, target adapter present, per-entry verdict, exit 1 on any incomplete swap.
- **`references/factory/` — six phase refs**: `00-intake` (≤10 questions, one pass) · `10-match` (script-decided ranking, shape taxonomy, canonical-stack policy, Lane-B honesty) · `20-clone` (consent, commit pinning, disk D, boot evidence) · `30-swap` (vendor→open-source target table, method, smoke tests) · `40-rebrand` (brand.json, injection points, the leak check, license duties, 6-row visual sanity) · `50-verify-deploy` (the 6-row verify tail, Coolify deploy, the owner-facing report).
- **`tests/test_factory.py`** — 13 tests: registry import/scoring/determinism/export, license blocking, swap gate (fails on vendor, passes on adapter, allowlist, missing map), clone gate (state files, fresh history, license refusal, non-empty folder refusal).

### Removed (deleted, not deprecated)
- `references/buildout/` — the whole engine: `00-start-from-boilerplate`, `10-design-assembly`, `15-reference-library`, `20-component-library`, `30-design-audit`, `40-verify-the-product`, `45-map`, `50-direction-competition`.
- `scripts/{map_check,registry_sync,styles_fetch,styles_pick,assemble_pick}.py` + their tests + fixtures.
- `data/{styles/,items/,registries.snapshot.json,allowlist.json,boilerplates.json}` (~11.5 MB of design-generation input), `templates/design-audit/`, `references/eval/`.
- **Reason:** those layers existed to *generate* a product — design systems, per-block component negotiation, composition locks, map/spec rigor. That generation is where the drift, the token burn and the "impressive but crappy" outcomes lived. The skill went from 12 MB to ~0.4 MB.

### Changed
- `SKILL.md` rewritten as the factory router: the promise, the 6-phase table, 10 hard rules (license gate · measured-not-claimed · canonical stack · disk D · remote-until-consent · evidence · budgets · honesty spine · lanes · refs-are-data), the script table, task→file routing, pitfalls, and a verification section that checks the registry/swap/clone gates.
- `tests/test_budget_lines.py` now gates the factory wiring — refs and scripts exist, SKILL.md routes to them, and the removed machinery may not reappear.
- **Kept:** lifecycle/jargon/playbooks/formats refs · `templates/qa/` (probe, frame, cdp.mjs, form-drive.js) · the deckhand-profile + `PENDING.md` + `OPS.md` rules · the hard-won evidence rules (freshness, write-path, occlusion, text floor) compressed into the 6-row verify tail.

Suite: **36 tests**, all offline (28 factory + 8 budget/wiring).

### Audit pass (same release, pre-publish)

A zero-context read of the skill found seven defects that the fixtures could not see, because they
only exist on a real clone; each is fixed with a regression test:

- **The swap gate could not reach exit 0 on any real project** — the scan counted its own
  `.factory/swap-map.json` (which quotes the vendor patterns) as leftover vendor code. `.factory` is
  now skipped; the gate is red only for the project's own files.
- **An empty swap map exited 0** — "nothing to verify" is not a pass: it is now exit 3 with the fix
  spelled out (`template_intake.py --repo …`, then re-clone).
- **The adapter half was vacuous** — prose targets (`socket.io-or-sse`, `middleware or none`) were used
  as literal needles, so they could never be satisfied. Targets now carry real identifier lists
  (any-of), and targets whose replacement is the owner's own code (`own-code`) or an allowed deletion
  (`removed`) prove ABSENCE only, recorded in the entry.
- **Adapters could be satisfied by a lint config** — `.oxlintrc.json` lists the `EventSource` global;
  adapter hits are now restricted to source files and `package.json`.
- **Short vendor names matched inside words** — `ably` hit "pro**bably**" in a README. Plain-word
  patterns are word-bounded; SDK-shaped patterns stay substring.
- **The licence gate was bypassable** — `--repo` skipped it entirely (a repo with no LICENSE cloned
  with exit 0). `--repo` now measures the licence live (GitHub API) or requires a LICENSE file on a
  local-path fixture.
- **`--ref <sha>` could not pin a commit** — `git clone --branch` only takes names; a sha is now
  fetched and checked out detached.
- **The map described the registry, not the clone** — the clone is scanned (`package.json`,
  `.env.example`, README) so a vendor used only in code still lands in the map, marked `local-scan`.
- **The match brief was truncated by the script** — the swap-cost reason sat at index 7 of a
  six-line cap; the script now prints up to 12 and rows only rank above 0.
- **The QA harness was French/LTR-only** — `form-drive.js` hardcoded the French form selector and
  receipt pattern; both are now injected by `cdp.mjs` from `QA_FORM_SEL` / `QA_RECEIPT_RE`.
- **Two dead-end instructions** — a re-import step that no gate read (and crashed without `url`), and
  a `calib.html` listed in the README that does not exist. Both corrected. The commit is now cut
  **before** the install so no `node_modules`/`.next` can enter commit 1.

## 0.7.0 — 2026-09-23

The composition layer — the fix for the second field test's verdict: every mechanical gate green, the page still "not a website" (no layout, layers, or composition; one text scroll + a bare form). Additive: builds that never touch references, the blueprint, or the visual gate behave exactly as before; existing locks stay valid (new lock content is optional/additive; `sections` is required at the direction arm's freeze).

### Added
- **`15-reference-library.md` — vendored real-site references (MIT, `Nutlope/inspo`)**: `py scripts/styles_fetch.py` pulls a pinned snapshot into `data/styles/` — 2,320 real pages with traced palettes, real font stacks, **measured type ramps**, macrostructures, fold-by-fold autopsies, northstars; 68 components with JSX; provenance — fully offline afterwards. `py scripts/styles_pick.py --query …` returns deterministic reference picks for a brief. Rules: every direction names 1–3 references + carried traits + adaptation deltas ("adapt, don't copy"); the measured guidance (hero ≤ first viewport; 80–160 px section rhythm; centered padded column) is pipeline rule; reference imagery stays a URL, never vendored.
- **Composition ownership + sections in the lock.** `lock.sections[<s>] = { id, registry, url, macro, reference, pickedAt }`; compose FIRST, then pick components. An empty `sections: {}` without `"_waived": "<reason>"` fails the freeze (D11).
- **Rendered visual gate (`40-verify-the-product.md` §2)** — V1–V12 judged on screenshots by a vision-capable reviewer (composition/focal point · hero discipline · layers · section rhythm · type ramp · imagery policy · proof layer · register check · reference adherence · scanability · the 50 ms test · **no dead interior**); fix→render→judge loop closes before handoff. Calibration baseline = the field-test artifact: if the gate cannot fail that page, the gate is broken. V12 was added *by* the field test: the hero graphic panel passed V3/V6 while two thirds of its frame was dead white — V3/V6 ask whether a layer exists, V12 asks whether the bounded region is filled.
- **QA instrument templates (`templates/qa/`)** — `probe.html` (dependency-free same-origin iframe harness: overflowPx, overflow offenders, heading sizes/boxes, section gaps, image/CTA boxes), `frame.html` (true-width screenshot wrapper), `calib.html` (width calibration — **retired in 0.8.0**; the README no longer lists it), plus **`cdp.mjs` + `form-drive.js`** (node 22+ CDP driver: exact layout width via `Emulation.setDeviceMetricsOverride`, a script evaluated in the page's own context, true-width PNGs, and a form driver that reports read-back, the API status, the receipt's rect at the moment it appears, occlusion at max scroll and at focus, the text floor). Field-tested rules carried in the templates: `--window-size=390,844` does NOT give a 390px layout (Chrome clamps windows to a 500px minimum — it false-positived a mobile-overflow finding before calibration); a harness in `public/` is only served if it existed at BUILD time; and two harness bugs that produced false results — a document-wide "receipt" matcher catching unrelated marketing copy, and a hit-test loop counting off-screen fields as occluded.
- **Hero mockups as direction artifacts** — `A-hero.html`/`B-hero.html` (static, tokens inline); PASS_2 judges the winner's render, not the prose.

### Changed
- **Map arm gains R8**: spec-mode `summary.md` carries a `blueprint:` block — every base slot resolves to an inventory id or `not_applicable: reason`; missing/unresolved slots FAIL the freeze (the rule that stops a lean run from silently deleting the page's layout shell).
- **Direction arm gains D9/D10/D11**: `reference:` line required in both drafts; both hero mockups required; a resolved `sections` record required in the merged lock.
- `11-spec-mode.md` (companion): inventories start from the section blueprint; on a one-pager every rendered block is an item; imagery defaults reconcile to a policy (never "no imagery"); charter band gains a lean-depth figure; `summary.md` carries the blueprint block.
- `10-design-execution.md` (companion): the **additive bar** (ten must-contains — composition, focal point, hero discipline, layers, imagery policy, proof layer, rhythm, type system, scanability, one deliberate moment) + **register check** (both known generated registers, not just gradient-SaaS) + reference-derivation section; restraint applies AFTER the bar; imagery/art-direction policy (absence is a defect, not modesty).

Suite: 92 tests (map_check.py now 63 — R8/D9/D10/D11 each carry known-bad fixtures).

## 0.6.1 — 2026-09-22

Companion wiring + the design loop's last gate. The `conversion-audit` companion (map schema, spec mode, anti-slop rules) is now a named actor at every stage that consumes it, and the built-result anti-slop check (INV-8) — until now promised in prose — is an implemented step of the product-verification ref.

- **MAP:** step 2 now says where a greenfield map comes FROM — authored first via the companion's spec mode (`conversion-audit/references/11-spec-mode.md`); no companion installed → hand-write `map/` per `45-map.md`'s layout, or state "no map — building directly" in one line (never silent).
- **DIRECTION:** step 3 names the anti-slop source it runs against (`conversion-audit/references/10-design-execution.md` — 5 tells, restraint rule, quality floor); step 4 clarifies that when the competition ran, its lock IS the lock — straight to assembly, no second design-brief round.
- **VERIFY:** `40-verify-the-product.md` gains **built-result anti-slop (INV-8)** — the 5 tells + subject-grounding + restraint rule re-run against the RENDERED output, so plan-level PASS_2 is no longer final; a design that read alive in the plan but drifted generic during the build fails before handoff. SKILL.md step 7 names it.

Suite: 81 tests (wiring-only; no gate logic touched).

## 0.6.0 — 2026-09-22

The map + the direction stage. Two new stage refs and one new mechanical gate — additive: builds without a map or without the competition behave exactly as in 0.5.0. Unreleased; folds into the pending release batch.

### Added
- **`45-map.md` — the build consumes the map**: charters → scope + build order; step/user-state fields + the edge registry → the states each screen must render; flow exits → link targets; the freeze gate `py scripts/map_check.py --map map` (depth-aware: lean = 6 core edge categories, full = all 11) that REFUSES the freeze on an incomplete map; graceful skip when no map directory exists (exit 0, "SKIP"). Field shape behind it: the three defects every mechanical gate missed were three blank map cells.
- **`scripts/map_check.py` — the freeze gate, two skip-graceful arms.** Map arm: charters count == inventory count · zero silent blanks (block keys like `step_sequence:` understood; empty table cells fail) · zero dead-ends (`dead_ends_found: []`, no `Y` rows) · `map_version` required · no unfilled `<placeholders>`, `[STATUS]` tags, or TBD/TODO/FIXME markers · no merged flow files. **Direction arm** (`--direction`): the 7 artifacts exist · forks table carries `criterion` + `cost` columns, every row resolved, ≤~5 forks · exactly ONE live `winner:` (a second winning doc must be annotated `retired`) · minority report present · PASS_2 carries ≥2 artifact+location citations · cost + `vindication:` logged · the merged lock parses, keeps every ref-10 key (colors 6-hex) and passes the ref-10 enums (`randomness`/`density`/`motion`; `seed` int; `vibes` list; `base` string). **Demonstrated to fail on known-bad input**: 36 tests, every rule with its own failing fixture — plus the cold-reader dry-run's own artifacts (conformed set → PASS; raw pre-schema set → FAIL, 3 table-shape flags).
- **`50-direction-competition.md` — two directors, one winner**: identical inputs, different mandates; compete on documents only (never two builds); **blind drafts** (finish A before writing B, no revision chain); disagreements must become named forks — **capped ~5, each with its deciding criterion pre-committed before the other position is read, 2–3 rounds max**; **evidence-or-downgrade** (un-evidenced claims get `[unverified]` and cannot decide a fork); merge by mechanism (per-fork rubric + fusion step; neither author merges alone) to exactly ONE direction + a format-compatible `design.lock.json` + decision record with a **minority report** (losing option + reopening evidence); irreconcilable forks escalate to the client (rule-based default if skipped); after the merge one chair runs the build and one owner runs the independent verification lane (**refutation default** — findings cite artifact + location); parallel teams only on a mechanical trigger (≥2 independent workstreams + frozen foundation); PASS_2 anti-slop against the winning plan; **cost + vindication log** (`direction/log.md` — and if the merge is not measurably better than the better single draft, say so plainly).

### Changed
- `SKILL.md` flow: a gated **Map** step and a **Direction** step before assembly — both skip gracefully; a FAIL on the map gate refuses the freeze.
- **Evidence-addendum refinements (2026-09-22)**: DIRECT — blind drafts, forks capped ~5 with pre-committed deciding criteria, evidence-or-downgrade, merge-by-mechanism + minority report, cost + vindication log, refutation-default verification lane. MAP — per-charter budget (~900–1600 tokens) + readiness standard (Actionable · Logical · Testable · Complete · Sufficient · Coherent), `map_version` + spec-delta discipline (append-only in the LIVE loop), acceptance criteria in Given/When/Then, and the light-lane guard (rising time-to-first-commit with flat escaped defects → cut depth, don't add process).
- **Cold-reader dry-run of the direction stage** (paper run, one agent, lawyer case): produced the full ref-50 artifact set (5 forks, all resolved; PASS_2 with 2 real revisions) — and its cold read caught what the stage lacked: the four gate items were unenforced, so the direction arm above now exists. Ref 50 gained the missing mechanics it exposed: a map-substitution branch (no map is never silent), the winner's-seed rule, escalation delivery (`PENDING.md` `DECISION:` item; no answer by freeze → `default-by-rule`), PASS_2 concreteness (both docs state candidate values), honest single-writer/blinding recording, and the `final.md` (mandate-level) vs `decision.md` (fork-level) split.
- **Ref-50 hardening (same day, from the dry-run's findings)**: winner-uniqueness, PASS_2-citation and lock-enum checks added to the direction arm; ref 50 gained authorship + independence (named scribe, no-overrule, DEGRADED MODE for single-writer runs, timestamps as the blinding witness), full escalation mechanics (question format, board `#escalations` / `PENDING.md` delivery, skip = decline OR timeout, worked example, `default-by-rule`), the append-only conformance convention, placement/skip-rule clarifications, and a no-catalog-fetch note at DIRECTION; ref 10 gains an additive `institutional` vibes bucket (existing locks stay valid). Verified: 65-test suite; gate PASS on the conformed dry-run set and a synthetic escalation drill; FAIL on both known-bad fixtures.
- `40-verify-the-product.md`: acceptance rows are GENERATED from the map when one exists (charter → probe, edge state → render check, exit → link check); the hand-built path is unchanged without a map.
- Router + verification bullets updated; budgets re-checked (SKILL.md ≤500 lines, every ref ≤~150 — now enforced by a budget test).

### Field-test №2 fix batch (same day — frictions F-22…F-75; every matrix target answered)

Field Test №2 ran the updated pipeline end-to-end on a frozen brief (held-out 32/40 = 80.0% zero-margin; H1/H2/H3 met, H4/H5/H6 failed; 3 recurrences). This batch closes the verdict's friction→fix matrix and its 12 carryover items. The pipeline was patched only AFTER the verdict; no frozen artifact (map / direction / site / registrar) was touched. A reader can tell field-tested 0.6.0 from shipped 0.6.0 by this block.

- **Recurrences, root-fixed:** F-49 — ref 00 gains the arbiter **conflict clause** (a starter that contradicts the frozen lock loses; strip or reject, never re-open a frozen design). F-35/F-46/F-47 — dark scheme / focus ring / state-transition motion get owners + mechanical checks: ref 10 adds optional lock keys `dark` (six color keys, 6-hex) + `focus_ring` (6-hex), validated by D7; coherence check **3** (`transition-`/`animate-`/`duration-` greps — `motion:"none"` ⇒ expect nothing, otherwise lock-governed durations only); the focus-ring rule (`--ring` remapped, one accent only); the dark-mode derivation requirement (both schemes ≥4.5:1, fills included). F-51 — the item pre-flight row now names undeclared package imports.
- **Row-set gaps (H5/H6):** ref 40 gains requested-width probes (explicit 320/360/375; `scrollWidth` vs the REQUESTED width — the old probe false-negatived a real 49 px overflow), per-route chrome rows (fragment targets resolve per route; unique titles), confirmation-visibility + occlusion rows (rect after the form collapses; `elementFromPoint` hit-tests), ADD-row coverage, charter-placeholder coverage, reachable-string rule, listener-derived kill PID, evidence rules (F-56/F-63).
- **Coherence pair:** F-24 — both SK2 templates use one gate-detectable fill marker `FILL_ME` (R7 rejects it; instructions no longer tell writers to keep gate-failing text). F-25 — acceptance rows have a home: required `## Acceptance rows` charter section, declared in ref 11, consumed verbatim by ref 40.
- **Gate (`map_check.py`):** D3 anchors `winner:` to line start (prose mentions pass); D8 blinding-witness check (two draft sha256 hashes or an explicit DEGRADED statement); D7 optional `dark`/`focus_ring` + `base` vocabulary (`radix`/`none`); `--allow-missing pass2` merge-time self-check (FREEZE stays strict); table parsing honors `\|` escapes; R6 accepts `not_applicable: reason`; R7 bans `FILL_ME`; map arm prints the ADD-row count on PASS.
- **Picker:** `assemble_pick.py` relevance floor — `any` generalists need ≥1 requested-tag hit (or the section keyword); zero-hit fallback candidates are excluded, loudly.
- **Carryover kit (`subagent-team-simulation`):** `templates/stage.py` (machine stamps — F-42: never type clocks), `templates/FIELD-TEST.md` (pre-registration, caps sized to method breadth F-73, instrument discipline F-65/F-66, held-out binding readings F-70, anonymization grep-verify F-72, input-vs-output lists F-75, sink labelling F-74); PROTOCOL rules 11–12 (stamps + relay re-measurement F-32; un-runnable marking); blind-grading ref step 5; web-probe-pitfalls instrument persistence + browser page-weight.
- **ID inventory:** MAP/DIRECT F-22–F-30, F-33–F-45 · PASS_2 F-46–F-48 · BUILD F-49–F-55, F-64 · VERIFY F-56–F-63, F-67–F-69 · HARNESS F-31, F-32, F-42, F-65, F-66, F-70–F-75.
- **Suite: 65 → 77 tests.** Every new/changed rule carries a known-bad fixture. The updated gate still PASSES the frozen field-test-№2 map + direction artifacts (no retro-break) and still FAILS its known-bad fixtures.

### Cold-read audit (pre-release — one zero-context reader per skill; every finding verified against the files, all answered)
Skill-side fixes: the freeze gate's docs are now runnable as written — the invocation runs **from the PROJECT root** with the script's path, the SKIP messages resolve the path they looked at and say where the gate should run from, and the fixture commands are documented (both arms pass from the skill's own dir); the direction arm's "exactly ONE live `winner:`" now also requires `final.md` among the declaring docs (two drafts annotated `retired` can no longer leave zero live directions +test); D2 validates the `cost` cell (+test); R7 covers `summary.md` and flow/edge placeholders and catches `<Q1>`/`<date>`-style tokens (+2 tests); the numbered greenfield flow gains the missing **Verify the product** step (ref 40 was unreachable from it) and renumbers; the direction competition's trigger is defined (default ON whenever a brief exists; skip = recorded decision); `45-map.md` documents the `.design` dot-directory, the fixture commands, the companion boundary (`conversion-audit` owns the map schema), and the corrected acceptance-file wording; ref 30's coherence wording matches the 3-of-3 gate (+reduced-motion added to its deliberate gaps); SKILL.md's design-audit claim names the full run (perf lives in the `lh` project, not `design:audit:fast`); the ref-budget test now covers every ref, not just `references/buildout/`; count claims corrected (this block + the verification bullet). **Suite: 77 → 81.**

## 0.5.0 — 2026-09-22

Product-verification phase + honest instruments. An independent first-user field test (one non-technical client, one local-only marketing site, six-role agent team) proved the pack's rules work — and that two of its gates returned confident wrong answers. Both are fixed at the root, and the missing product-verification phase is now a ref of its own.

### Added
- **`40-verify-the-product.md` — the product-verification phase**: acceptance-criteria → test-row mapping (one failing check fails the row; one raw log per row), applicability + fallback when the design-audit kit is absent (headless-browser probes, link crawl, the two coherence greps, a placeholder sweep that reads RENDERED copy), write-path verification (submit → sink gains exactly one line → kill-by-PID → restart → line survives; a local deliverable is graded on its sink, never declared untestable), the Windows kill-by-PID recipe with the rule **"if the listener count did not change, your kill did not happen — your proof is void"**, and the acceptance→state matrix (empty/loading/success/error — the error state must be RENDERED, not just returned). Router row added; `30-design-audit.md` cross-refs the pre-handoff sweep.
- Fresh-run ergonomics from the field test: path arbiter between the boilerplate and design-assembly refs; the lock schema now names its deliberate non-keys (type scale / spacing / focus / dark derivation) and the single token file (`src/app/globals.css` on create-next-app + Tailwind v4); `PENDING.md` seeding moved to "the moment the project directory exists" (greenfield kickoffs have no directory yet); a Windows `~` note for the portable files; the OFL "seeded surprise" no longer implies a bundled font list; the ref-load budget counts a cross-phase verification sweep as one task.
- Picker honesty (`assemble_pick.py`): a `NO TAG MATCH` warning (stderr) when zero picks matched the tags; the documented keyword-fallback line now fires when a section has no curated rows (previously unreachable); `--explain` prints per-pick reasoning.
- Install-step walkability: the fresh-scaffold `components.json` dead end is documented with the minimal file inline + `--yes` (the interactive prompt / `ERR_PNPM_IGNORED_BUILDS` trap); item-body pre-flight before install (empty `files` envelopes, stock-photo hosts, star markup, unresolvable imports/deps → reject + re-pick); the read-only-pack adoption path (`onboard --catalog-file` + install-by-URL + license evidence recorded in the project); a license-check fallback for `gh`-less environments.
- `onboard` refusals now print the allowlist entry shape (fields + a copy-pasteable example) and name `catalogUrl` as the fix when an index 404s.

### Fixed
- **`verify` could pass a mostly-gated registry** — `ok` required only ONE sampled item to be 200. Now `ok` requires EVERY sample free; a free/gated mix reads `mixed` and fails; the whole-pool default sample count is 12 (was 5) and every line prints its free ratio. (Live shape that used to pass: `[401,401,200,403,401]`.)
- **Live registries vanished from the snapshot** — `KEEP_STATUSES={"healthy"}` silently dropped every non-healthy directory entry (a live MIT 2.3k-star registry was invisible to `list`). The snapshot now carries every non-hidden entry with its `healthStatus`; `list` legend: `*` allowlisted · `*+` allowlisted AND onboarded · `~` filtered by health/score (kept; `--all` shows all); an explicit `--match` always shows the matched filtered row; the footer counts hidden rows — "absent from the list" can no longer read as "does not exist".
- **The coherence gate was unrunnable AND blind** — the `rg --pcre2` one-liner fails where ripgrep is absent and cannot see Tailwind palette utilities (a stock starter ships 8 the old gate passed). The gate is now a portable 2-of-2 pair (`grep -rnE` raw values + palette utilities) with the pitfall: a clean hex run is NOT coherence.
- Variety-gate precedence: an explicit client ban or brief constraint outranks the "≥3 registries per page" count; a zero-tag-hit pick is admissible evidence for invoking the override.
- Placeholder copy rule: a placeholder's visible text is client-facing — never instructions to the builder (a field test shipped "Swap in the real photo when it is ready" onto a page).
- `20-component-library.md`: absolute-path invocation for `library.py`; regression test added for `cmd_sync` end-to-end (a snapshot write ordering bug was caught by a live run: unhealthy entries must be carried and `healthy` counted before the write).

## 0.4.8 — 2026-09-22

- Docs-to-code fixes from the cold-read audit: the design-audit step now names the real driver commands (`pnpm design:audit` / `:fast` + the four CLI gates, ONE report via `design:fails`) and points at the one-time kit install (`templates/design-audit/README.md`); "refs are data" now distinguishes the pack's OWN refs (follow them; re-verify their commands) from externally sourced content (never execute unverified); premium/pro registries are allowed for their free/MIT items only, gated per-install with `registry_sync.py verify --item`; the verification list carries the hex gate's actual command; `gh` noted in compatibility.

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
