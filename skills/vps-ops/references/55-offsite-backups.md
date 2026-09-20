# 55 — Offsite backups (never on the same VPS)

**Purpose:** backups that survive the VPS itself. Default = **dual offsite targets: Backblaze B2 (primary) + Cloudflare R2 (secondary)**, small retention (3 copies) → flat usage, free tiers never fill.
**Use when:** a project goes live (day-one default), the user asks about backups/durability, or a drill/verification is due.
**Prereqs:** ref 30 done; ref 50 §5 for the local dump + pg_restore recipe. Coolify v4.3.23 endpoint facts below are source-verified against tag v4.3.23 — `[verify at live drill]` markers until exercised.

## 0. Prices of entry — human-once, ONE batched ask

| Step | Where | ~time |
|---|---|---|
| Backblaze: create account → **enable B2** → copy the master key (keyID + key) once. **No card** — and non-paying accounts are hard-capped (see below), so Caps & Alerts (card-gated) can be skipped | backblaze.com | 10 min |
| **Tigris** (default second target, card-free): sign up → create a bucket → create access keys | tigrisdata.com | 5 min |
| *Optional, only if a card is acceptable* — Cloudflare R2: **enable R2** (card dialog mandatory) → one token (Object Read & Write) or the “Create additional tokens” bootstrap template | dash.cloudflare.com | skip on the card-free path |
| Coolify S3 storages + schedules + drills | — | **agent, via API (below)** |

Field cheat sheet (endpoint has NO bucket name, no trailing slash, keep `https://`):

| | Backblaze B2 (primary) | Cloudflare R2 (secondary) |
|---|---|---|
| Endpoint | `https://s3.<region>.backblazeb2.com` (region from `b2_authorize_account` → `apiInfo.storageApi.s3ApiUrl`) | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` |
| Region | the region string itself (e.g. `us-west-004`) — wrong region breaks SigV4 | `auto` |
| Access/Secret | app key keyID / applicationKey | token id / SHA-256 of token value (API-minted) or the dashboard pair |
| Free tier | 10 GB, hard caps available, ops free, egress 3× stored | 10 GB, 1M/10M ops, free egress — but **soft cap (it just bills)** |
| Why this order | cheapest, hard-capped, fully API-driven after signup | zero egress = the drill source |

**Tigris** (card-free second target): endpoint `https://t3.storage.dev` · region `auto` · access-key pair from the dashboard · 5 GB free, zero egress · official MIT MCP (`npx -y @tigrisdata/tigris-mcp-server`, hosted `mcp.storage.dev`); Coolify partner. If signup ever asks for a card, fall back to **Filebase** (5 GB, `https://s3.filebase.io`, region `auto`, no card) or **Koofr via rclone** (§5).

**B2 without a card — verified Sept 2026:** non-paying accounts are hard-capped; crossing the boundary returns `403 cap_exceeded` / `transaction_cap_exceeded` — **refused, never billed** (no payment method, nothing to charge). Caps can NOT be set via API/CLI (UI only, card-gated) — so treat 10 GB as a wall: keep the backup set (versions included — B2 is versioned by default; add a “keep only the last version” lifecycle rule) under it, and **alert loudly on `cap_exceeded`** — a silent stop is the only real failure mode. Never shard accounts to dodge the limit (AUP). Egress free up to 3× stored.

## 1. Wire it in Coolify — API, not dashboard

```bash
# S3 destination (create → validate; volume schedules reject is_usable=false)
curl -sS -X POST "$COOLIFY_URL/api/v1/s3-storages" -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"b2-offsite","endpoint":"https://s3.us-west-004.backblazeb2.com",
    "bucket":"<bucket>","region":"us-west-004","key":"<keyID>","secret":"<key>"}'   # → {uuid}
curl -sS -X POST "$COOLIFY_URL/api/v1/s3-storages/<uuid>/validate" -H "Authorization: Bearer $COOLIFY_TOKEN"

# DB backup — ONE schedule PER target (a schedule carries exactly one s3_storage_uuid):
#   B2 at 02:00, R2 at 02:15. backup_now:true proves the first dump immediately.
curl -sS -X POST "$COOLIFY_URL/api/v1/databases/$DB_UUID/backups" -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H 'Content-Type: application/json' -d '{"frequency":"0 2 * * *","enabled":true,"save_s3":true,
    "s3_storage_uuid":"<B2_UUID>","backup_now":true,"database_backup_retention_amount_s3":3,
    "missing_backup_notification_days":2}'
curl -sS "$COOLIFY_URL/api/v1/databases/$DB_UUID/backups/<backup_uuid>/executions" -H "Authorization: Bearer $COOLIFY_TOKEN"
# success = status:"success" AND message without 'Warning: S3 upload failed' — then LIST THE BUCKET (below)

# Volume (uploads) backup — find the storage uuid first:
curl -sS "$COOLIFY_URL/api/v1/applications/$APP_UUID/storages" -H "Authorization: Bearer $COOLIFY_TOKEN"
curl -sS -X PUT "$COOLIFY_URL/api/v1/applications/$APP_UUID/storages/<storage_uuid>/backups" \
  -H "Authorization: Bearer $COOLIFY_TOKEN" -H 'Content-Type: application/json' \
  -d '{"frequency":"0 3 * * *","enabled":true,"save_s3":true,"s3_storage_uuid":"<B2_UUID>",
    "disable_local_backup":true,"stop_during_backup":true,"retention_amount_s3":3}'
curl -sS -X POST "$COOLIFY_URL/api/v1/applications/$APP_UUID/storages/<storage_uuid>/backups/run" -H "Authorization: Bearer $COOLIFY_TOKEN"
```

Same endpoints exist for **services**: `/api/v1/services/{uuid}/storages/...` `[verify at live drill: service-volume backups]`.

## 2. Alerts — point notifications at the app's mail chain

```bash
curl -sS -X PATCH "$COOLIFY_URL/api/v1/notifications/webhook" -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H 'Content-Type: application/json' -d '{"webhook_enabled":true,"webhook_url":"https://<domain>/api/mail-alert",
    "backup_success_webhook_notifications":false,"backup_failure_webhook_notifications":true}'
```

Events emitted: `backup_success`, `backup_failed`, `backup_missing`, `backup_success_with_s3_warning`. The app-side endpoint is a tiny guarded route that forwards `{subject,text}` (or the raw Coolify payload) into the mail chain (ref 70) — owner gets an email; no monitoring UI needed.

## 3. Verification — the only honest proofs

1. **List the bucket.** A “success” execution is a claim; the object is the proof. B2 has a plain REST API (`b2_list_file_names` with the app key — no SigV4 needed); S3 targets via `rclone ls`/`mc ls`.
2. **Object counts match retention** (3 per target) — retention DOES delete from S3; both rules (`amount/days`) are independent.
3. **Restore drill** (weekly/monthly): download the NEWEST object from EACH provider, `pg_restore` into a scratch container, run a sanity query (row counts + `max(created_at)`). Never trust "scheduled".
4. Record `status.json`-style results somewhere the weekly harness check reads; alert on silence, not only on errors.
5. **Watch for the cap.** Any `cap_exceeded` / `account_trouble` 403 in logs or Coolify execution messages = that provider stopped; alert it, don't retry-loop.

## 4. Restore reality (the one thing the API can't do)

**No restore endpoint exists in v4.3.23** — Coolify's Import Backup (file / server path / S3) is dashboard-only, gated by a typed phrase + account password. Agent path instead:
**fetch the object directly** (S3 API / `rclone copy` / `mc cp`) → `pg_restore` (recipe: ref 50 §5) → done. Fresh-VPS disaster: reinstall Coolify → recreate resources → restore DBs from the objects → redeploy from git (ref 60's cutover habits apply).

## 5. Deep layer (recommended): restic → both providers

The Coolify-native schedules above cover resource DBs + mounts. For **full-VPS disaster recovery** (Coolify's own `coolify-db`, EVERY database, every app volume — one consistent snapshot set):

- **restic** (BSD-2, single static binary) → two repos: **B2 (S3)** + the second target — **Tigris (S3)** by default, or **Koofr** (10 GB, no card, app-password auth) through restic's rclone backend: `-r rclone:koofr:coolify/restic-b -o rclone.program=/usr/local/bin/rclone` (verified end-to-end; serialize runs with `flock` — restic#5582; avoid Proton Drive — it blocks rclone — and Telegram — no rclone backend exists). `keep-last 3 --prune`; `check --read-data-subset=10%` (plain `check` reads NO data).
- `pg_dump --format=custom --no-acl --no-owner` per DB container incl. `coolify-db`; `tar czf` of an explicit volume allowlist; staging wiped+trapped per run — success only after BOTH providers hold the snapshot.
- **B2 trap:** restic's S3 backend hides deletions as versions — set the B2 lifecycle **“keep only the last version”** or storage grows silently.
- **Escrow `restic-*.pass` OFF the box** (password manager). Without it every backup is unreadable — one secret to rule the design.
- Weekly drill from the primary repo (B2, or whichever has free egress): freshness (<26 h) → subset check → restore latest → pg_restore into a throwaway `postgres:16` → sanity query → PASS heartbeat / FAIL email via the alert endpoint. Harness weekly check on `status.json` = the dead-man's switch (fires on silence).
- Ready-made: **`templates/vps-backup/`** (`coolify-backup.sh` + systemd units + secrets layout). `[verify at live drill]`

## 6. Known gaps (v4.3.23) — don't rediscover them live

No restore API (dashboard-only) · no GET for volume-backup schedules/executions · volume backups emit NO notifications · DB backups reject `disable_local_backup` (422; volume schedules accept it) · instance self-backup is API-less · file download is UI-only.
