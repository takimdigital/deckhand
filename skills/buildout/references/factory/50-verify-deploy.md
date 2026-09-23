# 50 — Verify & ship (≤15 calls, then deploy)

The verify tail is small on purpose: the template's own community tests the code; we verify
**our changes** (clone, swap, rebrand) and the owner's must-haves.

## The 6 rows

| # | check | evidence (pasteable) |
|---|---|---|
| 1 | fresh-clone boot | install/build/start log + a build id or asset hash proving the served page is this build (a 200 alone is not proof) |
| 2 | swap check | `swap_check.py` exit 0, every entry `OK` + the smoke test (auth: sign-up→session→protected page; db: migrate+write+read) |
| 3 | rebrand leak check | grep command + zero hits outside LICENSE/NOTICE/.factory |
| 4 | core flow write-path | drive the real conversion (form/sign-up/order) with `templates/qa/cdp.mjs` + `form-drive.js`; prove the write (row/email/file) and that the confirmation is inside the viewport at 390 and 1280 |
| 5 | mobile probe | overflow 0 at 320/390/1280; text floor ≥16px; controls ≥44px; occlusion at max scroll disclosed if any |
| 6 | PENDING | only mandatory facts outstanding (domain, email, legal, photos, payment, date) — nothing else blocks |

Acceptance = the owner's `must-have features` from intake, each with the row that proves it.
A row without a pasteable artifact is not a row.

## Deploy (vps-ops, Coolify)

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
