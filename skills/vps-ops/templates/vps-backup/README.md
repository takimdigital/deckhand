# vps-backup — the deep layer (restic → B2 + Tigris) — LIVE-VERIFIED 2026-09-20

One script, two offsite repos, weekly verified drill, plus a home-copy pull. Full rationale: ref `55-offsite-backups.md`.

## Install (agent, on the VPS)

1. `apt-get install -y jq` · restic: **upstream static binary** (apt lags) — `curl -fsSL -o /tmp/r.bz2 https://github.com/restic/restic/releases/latest/download/restic_<ver>_linux_amd64.bz2` (get `<ver>` from the releases API) → `bunzip2` (needs `bzip2` pkg) → `/usr/local/bin/restic`. rclone 1.75+ likewise if used for home/koofr paths.
2. Copy `coolify-backup.sh` → `/opt/backup/`, `chmod 700`. Create `/opt/backup/state`.
3. Create `/etc/backup/env` (root, 600, **LF line endings** — CRLF makes restic hang on a mangled repo path) with: provider hosts/buckets/keys/region, `ALERT_URL`, `VOLUMES` allowlist, `DB_CONTAINERS` (names = the plain uuids), `SANITY_DB`/`SANITY_SQL`.
4. Create the two repos ONCE (`restic init` with per-repo env — see the wrappers in the script) — then **escrow both passwords in the owner's password manager**. Lost password = lost backups, forever.
5. Run a first manual round-trip: `coolify-backup.sh backup && coolify-backup.sh verify` — only after BOTH pass, enable timers.
6. systemd (preferred over cron):

```ini
# /etc/systemd/system/coolify-backup.service
[Unit]
Description=Coolify offsite backup
[Service]
Type=oneshot
ExecStart=/opt/backup/coolify-backup.sh backup

# /etc/systemd/system/coolify-backup.timer
[Unit]
Description=Nightly Coolify offsite backup
[Timer]
OnCalendar=*-*-* 03:15:00
Persistent=true
[Install]
WantedBy=timers.target
```

Weekly verify = a second pair (`coolify-verify.service` → `ExecStart=/opt/backup/coolify-backup.sh verify`, `coolify-verify.timer` → `OnCalendar=Sun *-*-* 04:30:00`).
Enable: `systemctl daemon-reload && systemctl enable --now coolify-backup.timer coolify-verify.timer`.

## Drill findings baked into this template (2026-09-20)

- **Coolify DB users are per-container** (`coolify-db` → `coolify`; app DBs → the app name) — the script auto-detects via `printenv`; never assume `postgres`.
- **Executions endpoint can be empty** for on-demand Coolify dumps — list the bucket; the object is the proof. Re-triggering via `PATCH {backup_now:true}` is unreliable — DELETE + re-POST the config.
- **Wrong bucket class = 0-byte reads**: a GLACIER-class bucket lists objects (HEAD size correct) but every GET >~1 KB returns HTTP 200 + 0 bytes to every client (rclone `unexpected EOF`, python `IncompleteRead`). Create buckets via API (default STANDARD) — never accept a console default without verifying with a 512 KB round-trip (`scripts/tigris_bucket.py` does exactly that).
- **restic has no per-repo credentials** — inject `AWS_ACCESS_KEY_ID/SECRET` + `AWS_DEFAULT_REGION` per invocation (Tigris `auto`, B2 the bucket region).
- **The mail router rejects link-less bodies** — the alert route must append the app URL.

## A home copy (ref 55 §7 — choices ② and ③)

`local-pull.sh` runs on the USER'S machine (never the VPS): mode `cloud` mirrors the backup buckets down (restic repos included → a full local restore works); mode `vps` pulls fresh dumps straight off the server over SSH (works behind NAT). Schedulers: plain cron / **Windows Task Scheduler** (wrap in a `.cmd` → `bash.exe -lc …`; register with `schtasks /Create /TN … /SC DAILY /ST 10:00`) / an **agent cronjob** (Hermes needs its gateway installed & running or scheduled fires never happen). Windows notes: native exes need `C:/…` paths; **check the PC clock** — SigV4 fails ("Timestamp … is in the future") at >15 min skew (`w32time` + `w32tm /resync /force`, elevated). Optional local S3: RustFS in Docker (ref 56).

## Provider traps

- **B2:** lifecycle “keep only the last version” (set at bucket create, `scripts/b2_setup.py`) — restic's S3 backend hides deletions; hidden versions keep accruing. Card-less accounts are hard-capped — alert on `cap_exceeded`.
- **Tigris:** create buckets via API (STANDARD); deleted names sit in a ~10-min cooldown (`409 BucketInaccessible`) — pick a new name. 5 GB free — size the pruned set accordingly.

## What the harness checks weekly (dead-man's switch)

SSH in, read `/opt/backup/state/status.json`:
`status=ok` · `last backup < 26 h` · `last verify < 8 d` · both repo snapshot ids present. Silence = failure; alert the owner through the same mail chain.
