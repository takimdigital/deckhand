# vps-backup — the deep layer (restic → B2 + R2)

One script, two offsite repos, weekly verified drill. Full rationale: ref `55-offsite-backups.md` §5.

## Install (agent, on the VPS)

1. `apt-get install -y jq` · restic: install the **upstream static binary** (`apt` lags) and verify its sha256.
2. Copy `coolify-backup.sh` → `/opt/backup/`, `chmod 700`.
3. Create `/etc/backup/env` (root, 600) with: provider hosts/buckets, `ALERT_URL`, `VOLUMES` allowlist, `DB_CONTAINERS` (names = the plain uuids), `PGUSER`/`DBNAME`.
4. Create the two repos ONCE (restic init) — then **escrow both passwords in the owner's password manager**. Lost password = lost backups, forever.
5. Init the repos and run a first manual round-trip: `coolify-backup.sh backup && coolify-backup.sh verify` — only after that enable timers.
6. systemd (preferred over cron):

```ini
# /etc/systemd/system/coolify-backup.service
[Unit]
Description=Coolify offsite backup
OnFailure=owner-alert@%n.service
[Service]
Type=oneshot
ExecStart=/opt/backup/coolify-backup.sh backup

# /etc/systemd/system/coolify-backup.timer
[Unit]
Description=Nightly Coolify backup
[Timer]
OnCalendar=*-*-* 03:15:00
Persistent=true
[Install]
WantedBy=timers.target
```

Weekly verify = a second timer calling `ExecStart=/opt/backup/coolify-backup.sh verify` (Sunday 04:30).

## Provider traps

- **B2:** set the bucket lifecycle to **“keep only the last version”** — restic's S3 backend hides deletions, and hidden versions still accrue storage.
- **R2:** free egress makes it the drill source; B2 restores monthly at most (egress allowance = 3× stored).
- Provider-side caps/alerts on both (B2 Caps & Alerts is the hard stop).

## What the harness checks weekly (dead-man's switch)

SSH in, read `/opt/backup/state/status.json`:
`status=ok` · `last backup < 26 h` · `last verify < 8 d` · both repo snapshot ids present. Silence = failure; alert the owner through the same mail chain.
