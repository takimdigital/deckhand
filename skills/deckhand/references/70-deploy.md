# 70 — DEPLOY (proof, not hope)

**Objective:** the site is live on the owner's server and domain, with a passing smoke check, and the owner
holds a HANDOFF.md. **Output:** `dh phase done deploy`.

## First deploy (once per server/app) — runbooks in `references/ops/`
1. `00-user-checklist.md` — what only the owner can do (accounts, one key paste), batched.
2. Server: paid VPS → `10-bootstrap-vps.md` · $0 preview (Oracle Always Free) → `11-oracle-free-tier.md`
   (price sheet: `12-provider-price-sheet.md`).
3. Domain + TLS: `20-domain-dns-ssl.md` · free domain / Cloudflare → `21-free-domain-cloudflare.md`.
4. App: `30-deploy-app.md` (repo → Coolify app → env → Postgres → domain → first deploy → first-run data →
   `OPS.md`). Email: `70-auth-and-email.md`. Backups: `55-offsite-backups.md`. Uploads: `56-app-object-storage.md`.
5. Record the target: `dh deploy target --app <coolify-app-uuid> --url https://<domain>`.

## Every release
`dh deploy ship` = clean tree required → `git push` → Coolify deploy → wait for a terminal deployment of
THIS commit (a stale success is not success) → smoke (200 + brand name on the page) → `deploy.json`.
Failure → `dh deploy raw dlogs <uuid>`; rollback per `ops/40-change-pipeline.md`.

## Handoff
`dh handoff` → HANDOFF.md (live URL, where each secret lives, everyday commands, bots, verify summary,
open PENDING items, licences). Present it; `dh phase done deploy`. Free-preview deployments are labeled
"preview" everywhere; `ops/60-migrate-to-paid.md` is the exit.
