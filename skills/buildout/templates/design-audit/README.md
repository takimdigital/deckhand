# design-audit — the front-end quality gate

One command runs a 16-check design matrix against the running app and writes **one machine-readable
report** an AI agent can read cheaply. Assembled entirely from maintained open-source packages
(no custom test framework); the only hand-written pieces are two thin spec files that **wire**
those plugins together in a single page load per route.

## What it covers

| # | Check | Tool |
|---|---|---|
| 1 | Visual regression (pixel baselines per project) | Playwright `toHaveScreenshot` |
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
   - this folder → `<repo>/design-audit/`
   - `playwright.config.template.ts` → `<repo>/playwright.config.ts` (rename; **merge** if the repo already has one)
   - `design-audit/routes.example.json` → `<repo>/design-audit/routes.json` (rename)
   - `stylelintrc.template.json` → `<repo>/.stylelintrc.json` (optional, enables `design:css`)
   - `htmlvalidate.template.json` → `<repo>/.htmlvalidate.json` (optional, tunes `design:html`)
2. Merge `package.snippet.json` into the repo's `package.json` (devDependencies + scripts; keep the exact pins).
3. `pnpm install`
4. Install browsers: `pnpm exec playwright install chromium webkit firefox`
5. Fill the two values:
   - `playwright.config.ts` — you can leave the defaults if `pnpm build && pnpm start` serves on :3000;
     otherwise set `AUDIT_PORT` / `AUDIT_START_CMD` (env) or edit the two lines directly.
   - `design-audit/routes.json` — your real routes. `"key": true` on up to ~5 important pages (they get
     Lighthouse + OG asserts); `"smoke": true` on ONE page (the Firefox smoke visit).
     Noise allow-lists: `allow.console` / `allow.network` take substrings — add third-party noise here,
     never a real failure.

## Run

```bash
pnpm design:audit          # everything: 6 projects + Lighthouse
pnpm design:audit:fast     # the 4 visual projects only (day-to-day loop)
pnpm design:fails          # failures + summary ONLY — the file the AI reads
pnpm design:links          # link crawl (the app must already be running)
pnpm design:html           # HTML validity over the saved dumps
pnpm design:css            # stylelint JSON
pnpm design:lint           # eslint JSON
```

- **First run ever:** `pnpm design:audit:update` once, then **commit** `design-audit/tests/__screenshots__/`.
- After an intentional design change: `pnpm design:audit:update` → commit the diff. That commit *is* the review.
- A missing baseline **fails** on CI by design — baselines are never created silently.

## Baselines & determinism (the one hard rule)

Fonts render differently on Windows vs Linux, so baselines are keyed to a platform. Generate and
update them in **ONE environment** — the pinned Playwright container:

```bash
docker run --ipc=host -v "C:/path/to/repo:/work" -w /work mcr.microsoft.com/playwright:v1.63.0-noble \
  npx playwright test --update-snapshots
```

No Docker on the machine? **Degraded mode**: run natively (`pnpm design:audit:update`) on this one
machine only — and say so in your report. Never mix environments and never loosen
`maxDiffPixelRatio`/`threshold` to mask an OS difference.

## Reading failures (token discipline)

Read `pnpm design:fails` — never raw logs, the HTML report, or screenshots. Each failed test in
`design-audit/ctrf/ctrf-report.json` carries `filePath`, `message`, `trace`, and attachment paths
(`audit-<route>.json`, screenshots, `*-diff.png`, `trace.zip`, `lighthouse-<route>.json`).
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
├── tests/
│   ├── design-audit.spec.ts   # the 16-check unified spec (one load per route)
│   ├── perf.spec.ts           # Lighthouse pass (runs only in the `lh` project)
│   └── __screenshots__/       # committed baselines (per project), created on first update
└── reports/                   # generated CLI JSON lands here (README.txt keeps the folder)
```
