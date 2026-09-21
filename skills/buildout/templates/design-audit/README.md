# design-audit — the front-end quality gate

One command runs a 16-check design matrix against the running app and writes **one machine-readable
report** an AI agent can read cheaply. Assembled entirely from maintained open-source packages
(no custom test framework); the only hand-written pieces are two thin spec files that **wire**
those plugins together in a single page load per route.

## What it covers

| # | Check | Tool |
|---|---|---|
| 1 | Visual regression (pixel baselines per project) + stylesheet sanity (an empty-CSS build fails loudly, not as a wall of diffs) | Playwright `toHaveScreenshot` + layout assertion |
| 2 | Device matrix: desktop 1440 · mobile 393 (Pixel 5) · iPhone 14 (WebKit) | Playwright projects |
| 3 | Dark scheme + forced-colors/reduced-motion ready | Playwright `colorScheme` |
| 4 | Firefox smoke (tagged `@smoke` routes) | Playwright projects |
| 5 | WCAG 2.2 A/AA violations with failing nodes | `@axe-core/playwright` |
| 6 | Touch targets (< 24px) | layout assertion + axe `target-size` |
| 7 | Console errors | Playwright listeners |
| 8 | Page errors / unhandled rejections | Playwright listeners |
| 9 | Failed requests + 4xx/5xx responses | Playwright listeners |
| 10 | Horizontal overflow + **320px reflow** (WCAG 1.4.10) | layout assertion |
| 11 | `dir` (RTL readiness) recorded per route | layout assertion |
| 12 | Title / meta description / OG (key routes) | assertions |
| 13 | Performance + SEO + best-practices scores | `lighthouse` (CDP, `lh` project) |
| 14 | Broken links (full crawl) | `linkinator` |
| 15 | HTML validity | `html-validate` |
| 16 | CSS + JSX-a11y lint | `stylelint` + `eslint-plugin-jsx-a11y` |

## Install (one time)

1. Copy into the app repo:
   - this folder → `<repo>/design-audit/` — keep `routes.example.json` and the `*.template.*` files; they are the kit's masters, the installed copies are the renamed files below.
   - `playwright.config.template.ts` → `<repo>/playwright.config.ts` (rename; **merge** if the repo already has one)
   - `design-audit/routes.example.json` → `<repo>/design-audit/routes.json` (rename)
   - `stylelintrc.template.json` → `<repo>/.stylelintrc.json` (enables `design:css`)
   - `htmlvalidate.template.json` → `<repo>/.htmlvalidate.json` (tunes `design:html`)
   - `eslint.template.mjs` → `<repo>/eslint.config.mjs` — **only if** the repo has no eslint flat config; if it has one, add the `jsx-a11y` block to that config instead. (The template also wires the TypeScript parser, ignores build dirs, and registers `react-hooks` — without that last one, a repo's existing `eslint-disable` comments for `exhaustive-deps` surface as "rule not found" ERRORs.)
2. Merge `package.snippet.json` into the repo's `package.json` (devDependencies + scripts; keep the exact pins; **add** new keys, never overwrite the repo's own).
3. `pnpm install` — in an agent shell (no TTY) this can abort with `ERR_PNPM_ABORTED_REMOVE_MODULES_DIR_NO_TTY`; rerun as `CI=true pnpm install --no-frozen-lockfile` (the flag matters when the lockfile just changed).
4. Install browsers: `pnpm exec playwright install chromium webkit firefox`
5. Fill the two values:
   - `playwright.config.ts` — leave the defaults if `pnpm build && pnpm start` serves on :3000; otherwise pin per invocation: `AUDIT_PORT=3000 AUDIT_START_CMD='pnpm build && pnpm start' pnpm design:audit:fast`. A stale ambient `AUDIT_*` value silently retargets the whole gate — when an override is active the config prints the resolved values.
   - `design-audit/routes.json` — your real routes. `"key": true` on up to ~5 important pages (Lighthouse + OG asserts); `"smoke": true` on ONE page (the Firefox smoke visit). `allow.console` / `allow.network` take substrings for third-party noise — never a real failure. An entry needs the exact substring + its source + a review trigger; worked example: Next.js 15 emits `<link rel=preload as='stylesheet'>` (invalid `as`) → WebKit logs `<link rel=preload> must have a valid \`as\` value`, ignores the preload, CSS still loads — allowlist it and note "re-review when Next is upgraded". An allowlist without a reason is how a real bug hides.

## Run

```bash
pnpm design:audit            # everything: 6 projects + Lighthouse
pnpm design:audit:fast       # the 4 visual projects only (day-to-day loop)
pnpm --silent design:fails   # failures + summary ONLY — the file the AI reads (--silent keeps pnpm's banner out of the JSON)
pnpm design:links            # link crawl (the app must already be running)
pnpm design:html             # HTML validity over the saved dumps
pnpm design:css              # stylelint JSON
pnpm design:lint             # eslint JSON
```

- **First run ever:** `pnpm design:audit:update` once, then **commit** `design-audit/tests/__screenshots__/`.
- After an intentional design change: `pnpm design:audit:update` → commit the diff. That commit *is* the review.
- A missing baseline **fails** on CI by design — baselines are never created silently.
- **Exit codes are the gate:** `design:html`, `design:css`, `design:lint` exit non-zero when they find something (a red gate, not a crash). A `design:links` report with `"links": []` means the crawl saw nothing — sanity-check before trusting `"passed": true`.
- **First run on an existing codebase:** expect lint noise (stylelint-config-standard conventions, html-validate structure messages). Triage it — relax the rules you consciously accept (both templates ship the tuned-down batch, validated against a React 19 / Next 15 / Tailwind v4 app) rather than ignoring files.

## Pitfalls (validated against a React 19 / Next 15 / Tailwind v4 app)

- **A red gate with an EMPTY report is a config error, not findings.** Example: `at-rule-prelude-no-invalid` rejects `"off"` as an option value (it wants `null`) — stylelint then exits 2 with **0 warnings** in the JSON. Before chasing code, check the report's `errored` / `invalidOptionWarnings` fields.
- **Never add an `elements` override to html-validate** to tolerate a non-standard value (e.g. `<link as="stylesheet">`). It *replaces* the built-in element metadata and the whole audit explodes with bogus `element-name` / `no-self-closing` findings (1,700+ on one page). Turn the one rule off (`attribute-allowed-values`) and document the upstream cause instead.
- **`design:html` audits the RAW server response, not the hydrated DOM.** The spec fetches each route with `page.request.get` — auditing React's post-hydration DOM reports artifacts (hoisted `<title>` in `<body>`, `_R_`/`:B:0` ids, camelCase attrs, self-closed voids). If you add your own dumps, do the same.
- **Run order matters:** the audit's own run wipes `design-audit/artifacts/` at test start (Playwright `outputDir` semantics). Run `design:audit` first, then `design:html`, in the same session — a stale dump set validates nothing.
- **stylelint `--fix` can silently kill Tailwind v4.** Auto-fix rewrites `@import "tailwindcss"` → `@import url("tailwindcss")`; Tailwind v4 only resolves the string form, the build stays green, and the app ships with NO CSS (every visual baseline fails with a giant diff). The template pins `import-notation: "string"` for this reason. If you ever see a wall of huge screenshot diffs, check the CSS chunk exists first: `curl -s <url> | grep -o '/_next/static/[a-z0-9/]*\.css'`.
- **pnpm in agent shells / deploys:** `CI=true` implies `--frozen-lockfile`; after adding or re-pinning a dep, plain install refuses to repair the lockfile — run `CI=true pnpm install --no-frozen-lockfile` once and **commit `pnpm-lock.yaml`**. A drifted lockfile fails the DEPLOY (`ERR_PNPM_OUTDATED_LOCKFILE`), not the local build. And never pipe an install through `| tail` when its exit code matters — the pipeline reports tail's exit (0), not the install's.

## Baselines & determinism (the one hard rule)

Fonts render differently on Windows vs Linux, so baselines are keyed to a platform. Generate and
update them in **ONE environment** — the pinned Playwright container:

```bash
docker run --ipc=host -v "C:/path/to/repo:/work" -w /work mcr.microsoft.com/playwright:v1.63.0-noble \
  npx playwright test --update-snapshots
```

No Docker on the machine? **Degraded mode**: run natively (`pnpm design:audit:update`) on this one
machine only — never mix environments and never loosen `maxDiffPixelRatio`/`threshold` to mask an
OS difference. **Record which mode produced them in the update commit message**
(e.g. `design-audit: baselines (container)` / `(native, degraded)`) — that is how a reader of the
committed set can tell.

## Reading failures (token discipline)

Read `pnpm --silent design:fails` — never raw logs, the HTML report, or screenshots. Each failed
test in `design-audit/ctrf/ctrf-report.json` carries `filePath`, `message`, `trace`, and attachment
paths (`audit-<route>.json`, screenshots, `*-diff.png`, `trace.zip`, `lighthouse-<route>.json`).
Open a `*-diff.png` **only** when the visual change is ambiguous. Fix with `AUTO-FIX-PROMPT.md`.

## Gitignore (append to the repo's .gitignore)

```gitignore
design-audit/artifacts/
design-audit/ctrf/
design-audit/report/
design-audit/reports/*
!design-audit/reports/README.txt
```

(Never ignore `design-audit/tests/__screenshots__/` — those are committed baselines.)

## What it does NOT cover (deliberate — no maintained OSS package exists)

- keyboard-first walkthroughs / focus-order UX (axe covers basics only) — manual lens;
- logged-in flows — add a `storageState` per project when the app has a login wall;
- OG/meta *deep* validation beyond presence; RTL correctness beyond `dir` capture;
- email rendering, PDFs, native apps.

## Files

```
design-audit/
├── README.md                  # this file
├── AUTO-FIX-PROMPT.md         # the agent fix-loop prompt
├── package.snippet.json       # devDeps + scripts to merge
├── routes.example.json        # copy → routes.json
├── playwright.config.template.ts  # copy → <repo>/playwright.config.ts
├── stylelintrc.template.json      # copy → <repo>/.stylelintrc.json (if none exists)
├── htmlvalidate.template.json     # copy → <repo>/.htmlvalidate.json (if none exists)
├── eslint.template.mjs            # copy → <repo>/eslint.config.mjs (only if no eslint flat config)
├── tests/
│   ├── design-audit.spec.ts   # the 16-check unified spec (one load per route)
│   ├── perf.spec.ts           # Lighthouse pass (runs only in the `lh` project)
│   └── __screenshots__/       # committed baselines (per project), created on first update
└── reports/                   # generated CLI JSON lands here (README.txt keeps the folder)
```
