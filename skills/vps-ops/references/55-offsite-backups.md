# 55 — Offsite backups (never on the same VPS)

**Purpose:** backups that survive the VPS itself. Default = **dual offsite targets: Backblaze B2 (primary) + Tigris (secondary) — both card-free**; R2 optional (card holders). Small retention (3 copies) → flat usage, free tiers never fill.
**Use when:** a project goes live (day-one default), the user asks about backups/durability, or a drill/verification is due.
**Prereqs:** ref 30 done; ref 50 §5 for the local dump + pg_restore recipe. Coolify v4.3.23 endpoint facts below are source-verified against tag v4.3.23 — `[verify at live drill]` markers until exercised.

## 0. Prices of entry — human-once, ONE batched ask

| Step | Where | ~time |
|---|---|---|
| Backblaze: create account → **enable B2** → copy the master key (keyID + key) once. **No card** — and non-paying accounts are hard-capped (see below), so Caps & Alerts (card-gated) can be skipped | backblaze.com | 10 min |
| **Tigris** (default second target, card-free): sign up → create access keys. **The agent creates the bucket via API** (`scripts/tigris_bucket.py`, default STANDARD class) — never the console: a console-picked GLACIER class lists objects fine but serves every read >1 KB as **0 bytes** | tigrisdata.com | 5 min |
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

**Tigris** (card-free second target): endpoint `https://t3.storage.dev` · region `auto` · access-key pair from the dashboard (`tid_…` / `tsec_…`) · 5 GB free, zero egress · official MIT MCP (`npx -y @tigrisdata/tigris-mcp-server`, hosted `mcp.storage.dev`); Coolify partner. If signup ever asks for a card, fall back to **Filebase** (5 GB, `https://s3.filebase.io`, region `auto`, no card) or **Koofr via rclone** (§5). **Create buckets via API, not the console** (defaults to STANDARD; `scripts/tigris_bucket.py` also proves readability with a 512 KB round-trip). A deleted bucket NAME sits in a ~10-min cooldown (`409 BucketInaccessible "recently deleted"`) — pick a new name rather than waiting.

**B2 without a card — verified Sept 2026:** non-paying accounts are hard-capped; crossing the boundary returns `403 cap_exceeded` / `transaction_cap_exceeded` — **refused, never billed** (no payment method, nothing to charge). Caps can NOT be set via API/CLI (UI only, card-gated) — so treat 10 GB as a wall: keep the backup set (versions included — B2 is versioned by default; add a “keep only the last version” lifecycle rule) under it, and **alert loudly on `cap_exceeded`** — a silent stop is the only real failure mode. Never shard accounts to dodge the limit (AUP). Egress free up to 3× stored.

## 0b. Destination choices — ask ONCE, batched (offer, never force)

Same spirit as the Track P/F ask — one question at deploy time: **“Where should the backups live?”**

| Choice | What it means | Role |
|---|---|---|
| ① **Cloud dual** — B2 + Tigris | Both card-free, $0, nothing to run at home | **smart default** (recommend it) |
| ② **Cloud dual + a home copy** | The same cloud, PLUS a mirrored copy pulled down to the user's own machine on a schedule — a plain folder (default) **or a local RustFS S3 with a browseable console** (§7) | offer — belt & braces (3-2-1) |
| ③ **Home only** — no cloud accounts | Backups pulled straight off the VPS over the existing SSH key onto the user's machine (plain folder, or a local RustFS S3 — Docker Desktop; §7). Most private; least durable if that machine dies | offer — for anti-cloud users |

Rules: one choice per run · ③ keeps the same restic tooling (a local repo instead of cloud repos) so drills and alerts are unchanged · with only one target the retention math (§5) shrinks — say in one sentence that home must never become the only copy of anything irreplaceable, then respect the choice.

## 1. Wire it in Coolify — API, not dashboard

```bash
# S3 destination (create → validate; volume schedules reject is_usable=false)
curl -sS -X POST "$COOLIFY_URL/api/v1/s3-storages" -H "Authorization: Bearer $COOLIFY_TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"b2-offsite","endpoint":"https://s3.us-west-004.backblazeb2.com",
    "bucket":"<bucket>","region":"us-west-004","key":"<keyID>","secret":"<key>"}'   # → {uuid}
curl -sS -X POST "$COOLIFY_URL/api/v1/s3-storages/<uuid>/validate" -H "Authorization: Bearer $COOLIFY_TOKEN"

# DB backup — ONE schedule PER target (a schedule carries exactly one s3_storage_uuid):
#   B2 at 02:00, Tigris at 02:15. backup_now:true proves the first dump immediately.
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

Events emitted: `backup_success`, `backup_failed`, `backup_missing`, `backup_success_with_s3_warning`. The app-side endpoint is a tiny guarded route that forwards `{subject,text}` (or the raw Coolify payload) into the mail chain (ref 70) — owner gets an email; no monitoring UI needed. **The mail router rejects bodies with no link** — the route must append the app URL (`text: \`${text}\n\n${link}\``).

## 3. Verification — the only honest proofs

1. **List the bucket.** A “success” execution is a claim; the object is the proof. B2 has a plain REST API (`b2_list_file_names` with the app key — no SigV4 needed); S3 targets via `rclone ls`/`mc ls`.
2. **Object counts match retention** (3 per target) — retention DOES delete from S3; both rules (`amount/days`) are independent.
3. **Restore drill** (weekly/monthly): download the NEWEST object from EACH provider, `pg_restore` into a scratch container, run a sanity query (row counts + `max(created_at)`). Never trust "scheduled".
4. Record `status.json`-style results somewhere the weekly harness check reads; alert on silence, not only on errors.
5. **Watch for the cap.** Any `cap_exceeded` / `account_trouble` 403 in logs or Coolify execution messages = that provider stopped; alert it, don't retry-loop.
6. **0-byte reads?** rclone `unexpected EOF` / python `IncompleteRead(0 bytes…)` while HEAD shows the correct size = wrong bucket storage class (GLACIER). Recreate the bucket STANDARD (§0) — don't debug clients.

## 4. Restore reality (the one thing the API can't do)

**No restore endpoint exists in v4.3.23** — Coolify's Import Backup (file / server path / S3) is dashboard-only, gated by a typed phrase + account password. Agent path instead:
**fetch the object directly** (S3 API / `rclone copy` / `mc cp`) → `pg_restore` (recipe: ref 50 §5) → done. Fresh-VPS disaster: reinstall Coolify → recreate resources → restore DBs from the objects → redeploy from git (ref 60's cutover habits apply).

## 5. Deep layer (recommended): restic → both providers

The Coolify-native schedules above cover resource DBs + mounts. For **full-VPS disaster recovery** (Coolify's own `coolify-db`, EVERY database, every app volume — one consistent snapshot set):

- **restic** (BSD-2, single static binary — install the UPSTREAM build, apt lags) → two repos: **B2 (S3)** + **Tigris (S3)**. restic has no per-repo credentials → wrap per repo and inject keys+region per call: `rTG(){ AWS_ACCESS_KEY_ID=$TG_KEY_ID AWS_SECRET_ACCESS_KEY=$TG_SECRET AWS_DEFAULT_REGION=auto restic -r "s3:https://$TG_HOST/$TG_BUCKET/coolify" -p $TGPASS "$@"; }` / same for B2 with `AWS_DEFAULT_REGION=$B2_REGION`. (Koofr-via-rclone stays an option: `-o rclone.program=/usr/local/bin/rclone`; serialize with `flock` — restic#5582.) `keep-last 3 --prune`; `check --read-data-subset=10%` (plain `check` reads NO data).
- **DB users are per-container!** Coolify DBs are NOT `postgres` (coolify-db → `coolify`, app DBs → the app name): auto-detect with `docker exec <c> printenv POSTGRES_USER POSTGRES_DB`. `pg_dump --format=custom --no-acl --no-owner` per DB container incl. `coolify-db`; `tar czf` of an explicit volume allowlist; staging wiped+trapped per run — success only after BOTH providers hold the snapshot; `flock` serializes runs.
- **Env files must be LF.** A CRLF env makes restic read a mangled repo path (`bucket?/path`) and hang — write secrets/env with `\n` only.
- **B2 trap:** restic's S3 backend hides deletions as versions — set the B2 lifecycle **“keep only the last version”** or storage grows silently.
- **Escrow `restic-*.pass` OFF the box** (password manager). Without it every backup is unreadable — one secret to rule the design.
- Weekly drill from the free-egress repo (Tigris): freshness (<26 h) → subset check → restore latest → each dump into its own scratch DB → real sanity query on the APP db (`SANITY_DB`/`SANITY_SQL`) → PASS heartbeat / FAIL email via the alert endpoint. Harness weekly check on `status.json` = the dead-man's switch (fires on silence).
- Ready-made: **`templates/vps-backup/`** — `coolify-backup.sh` (all fixes baked in) + systemd units in its README. `[verified live 2026-09-20: both repos restored, sanity query passed, PASS email delivered — citiquiz drill]`

## 6. Known gaps (v4.3.23) — don't rediscover them live

No restore API (dashboard-only) · no GET for volume-backup schedules/executions · volume backups emit NO notifications · DB backups reject `disable_local_backup` (422; volume schedules accept it) · instance self-backup is API-less · file download is UI-only · on-demand `backup_now` re-trigger via PATCH is unreliable (DELETE + re-POST the config) · executions can stay empty for on-demand runs — **list the bucket, the object is the proof**.

## 7. Home copies (pull model — works behind NAT; the VPS is never asked to reach the home machine)

- **Choice ② — from the cloud:** `rclone sync b2:<bucket>/coolify ~/deckhand-backups/b2` (same for Tigris), or `restic copy` into a local repo. rclone/restic install once; credentials in a 0600 config.
- **Choice ③ — straight from the VPS:** the staging dir is transient by design (§5), so pull live: `ssh root@<vps> "docker exec <db-uuid> pg_dump --format=custom --no-acl --no-owner -U <user> <db>" > ~/backups/<db>.dump` and `ssh root@<vps> "docker run --rm -v <vol>:/src:ro alpine tar czf - -C /src ." > ~/backups/<vol>.tgz`, then `restic backup ~/backups` into a LOCAL repo (`restic -r /path/repo` — same tooling, so the drills and status checks carry over).
- **Local S3 target (offer): RustFS in Docker (Docker Desktop)** — the home copy lands in a *browsable* S3 instead of just a folder: the user gets a console UI (`http://localhost:9001` → the SPA at `/rustfs/console/`; `/` answers 403 to curl — fine in a browser), other local tools get an S3 endpoint. Ready-made: `templates/vps-backup/rustfs-local.compose.yml` — image `rustfs/rustfs:1.0.0` (pin, never `:latest`), **loopback-only** ports 9000/9001, creds via `.env`, named volumes for data+logs. Health: `curl -fsS http://127.0.0.1:9000/health` → `{"status":"ok"}`. rclone remote: `type=s3, provider=Minio, endpoint=http://127.0.0.1:9000, region=us-east-1, force_path_style=true`. Then set `LOCAL_S3_REMOTE=rustfs:<bucket>` in the pull's env file: each provider is mirrored into `rustfs:<bucket>/<provider>`; **target down (Docker Desktop off) = one logged skip, never a failed run** — the folder copy stays the belt. Docker Desktop is free for personal use; alternatives: Podman Desktop / Rancher Desktop / plain WSL2 docker. `[verified live 2026-09-20 on Docker Desktop: health OK at 18s, rclone put/get/delete + full mirror OK, readback magic PGDMP]`
- **Schedulers — use what the user has:** plain **cron / Windows Task Scheduler** (agent sets it up once; Windows: wrap in a `.cmd` → `bash.exe -lc …`, register via `schtasks /Create /TN … /SC DAILY /ST 10:00` — then obey the Windows trap list below) · an **agent cronjob** (“the bot” — a scheduled agent session that runs the pull, checks freshness, and emails on failure; **Hermes needs its gateway installed/running or scheduled fires never happen**) · the VPS-side systemd stays ONLY for VPS→cloud.
- **Windows home machines:** native tools need `C:/…` paths (not `/c/…` — e.g. rclone `--log-file` fails silently); **check the clock first** — SigV4 breaks (“Timestamp … is in the future”) when skew >15 min: start `w32time` + `w32tm /resync /force` (elevated), then retry.
- **Windows Task Scheduler — four silent killers (all live-hit 2026-09-20, all fixed in the `run-pull.cmd` template):** ① **bash path** — never assume `C:\Program Files\Git\bin\bash.exe`; discover with `where bash` (live case: the only MSYS bash was under a conda/pinokio env; `C:\Windows\System32\bash.exe` is the **WSL launcher**, not MSYS). ② **HOME** — pin it (`-lc "HOME=/c/Users/<you> bash <script>"`): the scheduler starts bash without a user profile, MSYS falls back to `/home/<user>`, the env file is not found → silent exit 1. ③ **PATH** — prepend `set "PATH=%USERPROFILE%\bin;%PATH%"` (rclone/restic live there; the scheduler env can lack it). ④ **conditions** — `DisallowStartIfOnBatteries`/`StopIfGoingOnBatteries` default to **true** (a laptop on battery = Last Result `0x800710E0` “The operator or administrator has refused the request”), and `StartWhenAvailable=true` is what makes a missed 10:00 **catch up after boot**. Write the `.cmd` **CRLF + ASCII only** (a stray `\b` escape byte inside a path = “filename … syntax is incorrect”), then **fire it once with `schtasks /Run` and require `Last Result: 0` + a fresh `pull OK` — an unverified schedule is not a backup.**
- **Pull-script traps (all baked into `local-pull.sh` v3):** the local-S3 probe MUST fast-fail (`rclone lsd <remote> --contimeout 5s --timeout 10s --retries 1 --low-level-retries 1`) — a stopped Docker Desktop otherwise makes the probe retry for MINUTES, eating an agent-tool timeout and *looking like a remote hang* (live: it got misread as a tigris failure while tigris answered in 0.3 s). Probe **once per run**, not per provider. Log every step start **and** `done … (Ns)` + final `pull OK (total Ns)` — start-only lines make a kill indistinguishable from a hang. Syncs get `--contimeout 15s --timeout 300s --retries 2 --low-level-retries 3`.
- **Counts & codes that lie:** zero-byte “directory marker” objects materialize as local FOLDERS — `find -type f` counts fewer files than `rclone lsf -R` objects (compare with rclone on both sides). A scoped key cannot ListBuckets: `rclone lsd b2:` at the root → 403 “not entitled” is EXPECTED; list the bucket (`rclone lsf b2:<bucket>`). rclone conf for B2-over-S3: `provider = Other` — newer rclone does not know `provider = Backblaze` (warns on every run).
- **Agent-driven pulls:** hand the run a GENEROUS timeout (600 s) and judge by the **log** (fresh `pull OK` + per-step timings), never by whether the tool call survived — and check log freshness FIRST, re-running only when actually stale.
- **Alerting from home:** POST to the deployed app's alert endpoint (public URL) — same path as §2; home-side failures are otherwise invisible.
- Ready-made: `templates/vps-backup/local-pull.sh` (both modes, **v3** — fast-fail probe, per-step timings) + `templates/vps-backup/run-pull.cmd` (the hardened Windows Task Scheduler wrapper). `[verified live 2026-09-20: rclone sync of both buckets to the home PC, restic repos included → local restore works; scheduler leg live-fired with Last Result 0]`
