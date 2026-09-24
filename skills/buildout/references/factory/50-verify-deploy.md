# 50 — Verify & ship (≤15 calls, then deploy)

The verify tail is small on purpose: the template's own community tests the code; we verify
**our changes** (clone, swap, rebrand) and the owner's must-haves.

## Coolify, measured (from a real Next.js + Postgres deploy)

- The image must install devDependencies even for a production build: Coolify builds with
  `NODE_ENV=production` in the environment, so a plain `npm ci` drops the PostCSS/Tailwind plugin and
  drizzle-kit, and the build dies with `Cannot find module '@tailwindcss/postcss'`. Use
  `NODE_ENV=development npm ci --include=dev` in the deps stage.
- **No database reads during `next build`.** Migrations run at container start, so the first build of
  a fresh deployment sees an empty schema and any prerendered page that queries it fails with
  `Failed query: select ...` / `parserOpenTable` — not with a connection error. Mark live-data
  segments `export const dynamic = 'force-dynamic'`.
- A bare-IP FQDN gives 502 from the proxy; a published port mapping (`3080:3000`) is the reliable
  temporary address until DNS exists.
- The Coolify token file (`export KEY = value`, spaces) is not sourceable — parse it. Its dashboard is
  loopback-only: tunnel with a local port outside the host's excluded ranges.
- Private repo: generate a deploy key on the VPS, add it as a read-only repo key, register it with
  `POST /api/v1/security/keys`, then create the app with `POST /api/v1/applications/private-deploy-key`.

## CI on GitHub — the traps, measured

- **Templates that validate env at import time** (`@t3-oss/env-nextjs`, a zod schema in
  `src/libs/Env.ts`) kill every job that was not given a value: build, static checks and unit tests all
  die with `Invalid environment variables` before running anything. Add a workflow-level `env:` block of
  throwaway values (the DB URL can point at the PGlite port the jobs start themselves). None of it is a
  secret, and without it every red X is about the workflow, not the code.
- **better-auth rate limits by default in production** (a few sign-ins per window), and Playwright runs a
  production build — a suite that signs in repeatedly gets `429 Too many requests` and a login form that
  silently stays put. Give the test stack an explicit opt-out (`RATE_LIMIT_DISABLED=true`, set only in
  `playwright.config.ts`'s `webServer.env`, honoured only when `NODE_ENV=production`) and keep the limiter
  live for real deployments.
- **A stateful e2e suite runs one browser.** Specs that seed a virgin database ("the first account becomes
  admin", empty-state assertions) cannot replay against the same server: the second browser project trips
  on preconditions the first consumed (24 passed / 2 failed is the signature). CI runs a single project;
  extra browsers are opt-in. Delete template jobs that test what the swap removed (Storybook with zero
  stories fails on noise).
- **The browser auth client must resolve its baseURL from `window.location.origin`**, never a build-time
  `NEXT_PUBLIC_*` value: the baked port breaks previews, test stacks and any deployment whose port differs
  from the build's. SSR keeps reading the env.
- Before pushing, run the workflow's own commands locally in the mode CI uses (`CI=1 <command>`):
  production build, rate limits on, one worker. Dev mode hides all three, which is how a green local suite
  turns into a red CI run.

## Phased mode — gate G4

Deploy runs only on the owner's explicit go, in its own turn. The verify rows may all be green before
that; green is not permission. When the go arrives, deploy, smoke-test the deployed container, and
report — then the run is done.

## The 6 rows

| # | check | evidence (pasteable) |
|---|---|---|
| 1 | fresh-clone boot | install/build/start log + a build id or asset hash proving the served page is this build (a 200 alone is not proof) |
| 2 | swap check | `swap_check.py` exit 0, every entry `OK` or `REMOVED` + the smoke test (auth: sign-up→session→protected page; db: migrate+write+read). Exit 3 = the map is empty: not a pass, measure the vendors first |
| 3 | rebrand leak check | grep command + zero hits outside LICENSE/NOTICE/.factory |
| 4 | core flow write-path | drive the real conversion (form/sign-up/order) with `templates/qa/cdp.mjs` + `form-drive.js`; prove the write (row/email/file) and that the confirmation is inside the viewport at 390 and 1280. **For a non-French / RTL locale pass `QA_FORM_SEL` + `QA_RECEIPT_RE`** (the defaults are the French originals) — otherwise `receipt: {found:false}` is the harness, not the site |
| 5 | mobile probe | overflow 0 at 320/390/1280; text floor ≥16px; controls ≥44px; occlusion at max scroll disclosed if any |
| 6 | PENDING | only mandatory facts outstanding (domain, email, legal, photos, payment, date) — nothing else blocks |

Acceptance = the owner's `must-have features` from intake, each with the row that proves it.
A row without a pasteable artifact is not a row.

## Deploy (vps-ops, Coolify)

**Server floor before anything else:** Coolify wants **≥2 vCPU / 2 GB RAM** (4 GB+ comfortable) and
the app itself adds to that. A "$5 VPS" is often below it — check the owner's spec at intake and say
so plainly *before* matching, instead of discovering it at deploy (`vps-ops` carries the price sheet
and the free-preview track).

**Runner first:** if the template sets `output: "standalone"`, the deploy command is
`node .next/standalone/server.js` (or its Dockerfile) — **not** `next start`, which warns and
behaves differently. Note the port the app actually listens on (templates sometimes hardcode it in
`scripts.start`) and set Coolify's port accordingly.

1. Project pushes to its own repo (the owner's account, fresh history).
2. Coolify on the VPS: app from the repo, Dockerfile/nixpacks, env vars from `.env.example`.
3. Postgres container + volume + scheduled backup; the app connects over the internal network.
4. Domain + TLS; email sending verified (SPF/DKIM on the sending domain); one real test email received.
5. Migration run on deploy; the app answers the core flow on the real domain.
6. Go-live checklist handed over: the PENDING items in the order they can be done, plus where the
   backups live and the one command to redeploy.

## Report (this is the whole deliverable to the owner)

```
<business> — shipped
template: <name> @ <commit> | license <spdx>
swaps: <n> done (<vendor→target>, …) | unproven: <list>
verify: 6/6 rows — evidence: <paths/commands>
PENDING (nothing else blocks): domain, email, legal, photos, payment, date
residuals: <anything measured that is not perfect, stated plainly>
```

No adjectives, no ceremony. If a row fails, the report says which one and what it costs to fix —
the owner decides, not the pipeline.
