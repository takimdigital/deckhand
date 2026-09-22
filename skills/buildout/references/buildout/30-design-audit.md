# 30 — Design audit (the front-end verification gate)

Load when: the UI is about to be called done (before deploy/handoff), or any design-facing change landed and needs proof. Ships as a copy-in kit: `templates/design-audit/`.

## What it is

One command runs a 16-check design matrix and emits ONE machine-readable report an agent reads cheaply: visual baselines + committed-CSS presence (an unstyled build fails loudly) · device matrix (desktop 1440 / Pixel 5 / iPhone 14 WebKit / Firefox smoke) · light+dark+forced-colors/reduced-motion checks · WCAG 2.2 A/AA via axe · console+page errors · failed + 4xx/5xx requests · horizontal overflow (+ 320px reflow) · touch targets (24×24, non-inline) · title/description/OG · Lighthouse perf+SEO+best-practices · link crawl · HTML validity · CSS + jsx-a11y lint.

Stack pins live in `templates/design-audit/package.snippet.json` — all permissive OSS; `@axe-core/playwright` is MPL-2.0 (consume-only, no obligations). Every tool emits its own standard JSON — the pack adds **no custom serialization**; the CTRF reporter merges test results, CLI tools write beside it, and `pnpm design:fails` (a one-line node filter) is the ONLY thing the agent reads.

## The loop

1. Install per `templates/design-audit/README.md` (copy-in, deps merge, browsers, fill `playwright.config.ts` + `routes.json`).
2. First time only: `pnpm design:audit:update` → **commit** `design-audit/tests/__screenshots__/`.
3. `pnpm design:audit:fast` → `pnpm --silent design:fails`.
4. Fix with `templates/design-audit/AUTO-FIX-PROMPT.md` (reads ONLY the filtered failures).
5. Re-run scope: `pnpm exec playwright test --grep "<name>"` — max 3 iterations per failure.
6. Green = zero axe A/AA · zero console/page errors · zero failed/4xx (minus allow-lists) · no overflow at 320 + project widths · perf ≥ budget · zero broken links · html/lint clean.

## Determinism rules (hard)

- Baselines live under a platform key (`__screenshots__/{platform}/…`: win32 / linux / darwin) so container and native sets coexist and are never compared across environments. Generate/update each set in ONE environment — preferred: the pinned container (`mcr.microsoft.com/playwright:v1.63.0-noble`; validated recipe in the kit README: app on host via `AUDIT_BASE_URL=http://host.docker.internal:3000` + `AUDIT_NO_SERVER=1`, repo copied inside the container so the host's node_modules is untouched, second comparing pass = determinism proof). No Docker = degraded same-machine mode — say so in the report and in the baseline-update commit message (`(container, linux)` / `(native, win32, degraded)`); never mix environments; never loosen `maxDiffPixelRatio`/`threshold` to mask an OS render diff. When you pin `AUDIT_PORT`/`AUDIT_START_CMD`/`AUDIT_BASE_URL` overrides, pin them per invocation — a stale ambient value silently retargets the gate (the config prints the resolved values whenever an override is active).
- Baselines change ONLY via explicit `update` commits — that commit is the review. Never edit snapshots, delete assertions, or skip to make a real failure pass.
- Upstream-noise allowlist entries (`routes.json` → `allow.console`/`allow.network`) need three things: the exact message substring, its source, and a review trigger. Worked example: Next.js 15 emits `<link rel=preload as='stylesheet'>` for a CSS chunk — an invalid `as` value; WebKit logs `<link rel=preload> must have a valid \`as\` value` and ignores the preload, the CSS still loads normally. Not app code → allowlist the exact message, note "re-review when Next is upgraded". An allowlist entry without a reason is how a real bug hides.
- On a deployed app (`OPS.md` present): run `design:audit:fast` (+ `design:links`) as an optional pre-release gate for user-facing changes, and add the design line to the ship receipt (`vps-ops` ref 40).

## Token discipline

Read `pnpm --silent design:fails` — never raw logs, the HTML report, or screenshot folders. (`--silent` keeps pnpm's banner out of the JSON.) Open a `*-diff.png` only when the visual delta is ambiguous. Evidence files on disk: `design-audit/ctrf/ctrf-report.json` (spine; attachments carry paths), `design-audit/artifacts/` (screenshots/traces/audit JSONs), `design-audit/reports/*.json` (links/html/css/lint).

## Gaps (deliberate — no maintained OSS package exists)

Keyboard-walkthrough UX and focus-order judgement (axe covers basics only) · logged-in flows (add `storageState` per project when the app has auth) · OG/meta beyond presence · RTL beyond `dir` capture · reduced-motion (captured for the record, never judged). Those belong to the manual/`dogfood` lens, not this gate. The coherence checks (raw values + palette utilities + state-motion — 3 of 3, `10-design-assembly.md` Phase 3) and the product-acceptance pass (`40-verify-the-product.md`) are separate gates — run the three together in one pre-handoff sweep.

## Triage & traps (all validated in anger)

- A gate that is red with an EMPTY report is a config error: stylelint `at-rule-prelude-no-invalid` wants `null`, not `"off"` (exit 2, zero warnings — check `errored`/`invalidOptionWarnings` in the JSON before chasing code).
- Never give html-validate an `elements` override to tolerate a non-standard attr value — it replaces the built-in element metadata and produces thousands of bogus `element-name`/`no-self-closing` findings. Turn the one rule off (`attribute-allowed-values`) and record the upstream cause.
- `design:html` validates RAW server-response dumps written by the audit's own run — Playwright wipes `artifacts/` at each start, so audit first, validate second, same session. The spec fetches with `page.request.get` on purpose: the hydrated DOM yields hoisted-title / `_R_`-id artifacts.
- stylelint `--fix` rewrites `@import "tailwindcss"` → `url(...)`, which Tailwind v4 does not resolve — build stays green, CSS is empty, every baseline fails large. `import-notation: "string"` is pinned in the template.
- Lockfile discipline: `CI=true` means frozen — repair with `CI=true pnpm install --no-frozen-lockfile`, then commit `pnpm-lock.yaml`. A drifted lockfile fails the DEPLOY (`ERR_PNPM_OUTDATED_LOCKFILE`), not the build; never `| tail` an install whose exit code matters.
