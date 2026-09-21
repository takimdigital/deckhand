# 30 — Design audit (the front-end verification gate)

Load when: the UI is about to be called done (before deploy/handoff), or any design-facing change landed and needs proof. Ships as a copy-in kit: `templates/design-audit/`.

## What it is

One command runs a 16-check design matrix and emits ONE machine-readable report an agent reads cheaply: visual baselines · device matrix (desktop 1440 / Pixel 5 / iPhone 14 WebKit / Firefox smoke) · light+dark · WCAG 2.2 A/AA via axe · console+page errors · failed + 4xx/5xx requests · horizontal overflow (+ 320px reflow) · touch targets · title/description/OG · Lighthouse perf+SEO+best-practices · link crawl · HTML validity · CSS + jsx-a11y lint.

Stack pins live in `templates/design-audit/package.snippet.json` — all permissive OSS; `@axe-core/playwright` is MPL-2.0 (consume-only, no obligations). Every tool emits its own standard JSON — the pack adds **no custom serialization**; the CTRF reporter merges test results, CLI tools write beside it, and `pnpm design:fails` (a one-line node filter) is the ONLY thing the agent reads.

## The loop

1. Install per `templates/design-audit/README.md` (copy-in, deps merge, browsers, fill `playwright.config.ts` + `routes.json`).
2. First time only: `pnpm design:audit:update` → **commit** `design-audit/tests/__screenshots__/`.
3. `pnpm design:audit:fast` → `pnpm design:fails`.
4. Fix with `templates/design-audit/AUTO-FIX-PROMPT.md` (reads ONLY the filtered failures).
5. Re-run scope: `pnpm exec playwright test --grep "<name>"` — max 3 iterations per failure.
6. Green = zero axe A/AA · zero console/page errors · zero failed/4xx (minus allow-lists) · no overflow at 320 + project widths · perf ≥ budget · zero broken links · html/lint clean.

## Determinism rules (hard)

- Baselines are generated ONLY in `mcr.microsoft.com/playwright:v1.63.0-noble` (Docker). No Docker = degraded same-machine mode — **say so in the report**; never mix environments; never loosen `maxDiffPixelRatio`/`threshold` to mask an OS render diff.
- Baselines change ONLY via explicit `update` commits — that commit is the review. Never edit snapshots, delete assertions, or skip to make a real failure pass.
- On a deployed app (`OPS.md` present): run `design:audit:fast` (+ `design:links`) as an optional pre-release gate for user-facing changes, and add the design line to the ship receipt (`vps-ops` ref 40).

## Token discipline

Read `pnpm design:fails` — never raw logs, the HTML report, or screenshot folders. Open a `*-diff.png` only when the visual delta is ambiguous. Evidence files on disk: `design-audit/ctrf/ctrf-report.json` (spine; attachments carry paths), `design-audit/artifacts/` (screenshots/traces/audit JSONs), `design-audit/reports/*.json` (links/html/css/lint).

## Gaps (deliberate — no maintained OSS package exists)

Keyboard-walkthrough UX and focus-order judgement (axe covers basics only) · logged-in flows (add `storageState` per project when the app has auth) · OG/meta beyond presence · RTL beyond `dir` capture. Those belong to the manual/`dogfood` lens, not this gate.
