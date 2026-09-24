# 30 — Stack swap (proprietary service → open source)

One dep at a time. The map is data (`.factory/swap-map.json`), the proof is a script run.

## Targets

| vendor detected | target | notes |
|---|---|---|
| clerk, next-auth, auth0, okta | **better-auth** | sessions, email+password, OAuth later |
| neon, planetscale, atlas, supabase-db | **docker postgres** | one container + volume + backups |
| upstash | **redis** (container) | only if the template really uses queues/cache |
| resend, sendgrid, mailgun, postmark | **SMTP** | nodemailer/`smtplib`; provider = the owner's mail host |
| aws-sdk, cloudinary, uploadthing | **minio** | S3-compatible, self-hosted |
| sentry | **glitchtip** or *none* | a solo business often needs neither |
| plausible, posthog, google-analytics | **umami** | self-hosted analytics |
| algolia | **meilisearch** | container |
| pusher, ably | **SSE / socket.io** | fewer moving parts, no vendor |
| openai | **ollama** (local) or keep | keep when hosted quality is the product |
| vercel (platform) | **coolify on the VPS** | Dockerfile/nixpacks |
| stripe, paddle, lemonsqueezy, polar | **keep** | a processor is a service, not a code lock-in — replace only with the owner's local method (invoice, bank transfer) |

## Method (per swap)

1. Read the map entry: `vendor`, `patterns`, `target`, `target_patterns`, `allow`, `note`.
2. Find every usage: `py scripts/swap_check.py --project D:/<slug>` prints files + lines.
3. Replace the SDK with the target: keep the same call sites/interfaces where possible; add the
   adapter (e.g. `src/lib/auth.ts` exporting the template's expected `auth()`/`getSession()` shape).
4. Add the new env vars to `.env.example` (names only — no values).
5. Re-run `swap_check` → every entry `OK`.
6. Smoke test the swapped path, not the greeting: auth = sign-up → session → protected route;
   db = migration + write + read one row; storage = upload + fetch one file. The runnable
   instrument is the verify tail (`50-verify-deploy.md` row 4, `templates/qa/`) — reuse it,
   never invent a fresh curl.
7. Only then record it: set `"status": "done"` + `"verified_at"` on the map entry and append the
   evidence (the `swap_check` run + the smoke output) to `.factory/scorecard.md`. Updating the
   *registry* row is optional and must be a full row — `templates_db.py import` needs `name` and
   `url` and dies with `NOT NULL constraint failed: templates.url` without them. No gate reads
   `verified: true`; the evidence in the scorecard is what a later reader trusts.

## Vendor-coupled tooling hides in devDependencies

The swap map must include the test/QA tooling, not only runtime services: a template's e2e suite can
depend on a paid cloud (measured: a Playwright suite importing `@chromatic-com/playwright`, plus
Checkly/Crowdin CI coupling) and then a typecheck or a test run fails for reasons that have nothing to
do with the owner's business. Either swap it for the open equivalent or remove the dependency *and*
its config in the same pass — leaving a half-removed reference is what breaks `tsc` later.

## Rules

- **Targets that are your own code.** `glitchtip or none`, `middleware or none`, `db-backed flags`
  and `keep-or-provider-sms` have **no library to grep for** — those entries carry
  `status: "own-code"` (or `"removed"`) and the gate proves ABSENCE only; the decision is the record.
  Everything else must show a real replacement: one of the entry's `target_patterns` in the code or
  `package.json` (the patterns are identifiers from the vendor table — never the prose target).
- **`target_patterns` is any-of:** one alternative satisfies the entry (`socket.io` **or**
  `eventsource` for the realtime target). If you pick an option the table doesn't list, add it to
  that entry's `target_patterns` in the map *before* claiming the swap is proven.
- **Swap before build when the template validates env at build time** (zod/env schemas asking for
  `CLERK_…`, `STRIPE_…`, `SENTRY_…`, `DATABASE_URL`, …): with the vendor key absent the build fails
  for reasons that have nothing to do with the owner's project. Prove the build after the swap.
- The vendor name may survive **only** in `allow` globs (docs/changelog) — `swap_check` enforces it.
- No "compatible" shims that keep calling the vendor SDK; the check greps for the SDK, not the brand.
- A swap that isn't in the map is not a swap — update the map first, then the code.
- Unproven swaps stay `verified: false`, and the registry row keeps the cost visible at match time.
- If a swap turns out bigger than a day (rewriting the auth model), stop and report it as a
  scope decision to the owner: keep the vendor, or accept the work. Never silently half-swap.

## Definition of done

`swap_check` exits 0 with every entry `OK` **and** the smoke tests above have pasteable output.
