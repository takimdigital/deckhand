#!/usr/bin/env bash
# vps-ops HOME-side pull (ref 55 §7) — runs on the USER'S machine, NOT the VPS.
# Choice ②: mirror the cloud backup buckets. Choice ③: pull dumps straight from the VPS over SSH.
# Schedule it with: cron / Windows Task Scheduler / a Hermes cronjob ("the bot").
# [verify at live drill — template]
#
# ~/.deckhand-backup.env (chmod 600):
#   MODE=cloud|vps
#   CLOUD_REMOTES="b2:my-bucket/coolify tigris:my-bucket/coolify"     # MODE=cloud
#   VPS=root@95.111.246.69  SSH_KEY=~/.vps-ops/ssh/id_ed25519         # MODE=vps
#   DB_CONTAINER=<db-uuid>  PGUSER=postgres  DBNAME=postgres
#   VOLUMES="rustfs-data myapp-uploads"
#   DEST=~/deckhand-backups
#   LOCAL_REPO=""            # optional: path to a LOCAL restic repo (restic init once)
#   ALERT_URL=https://<app-domain>/api/mail-alert                    # optional owner email on failure
set -euo pipefail
source ~/.deckhand-backup.env
mkdir -p "$DEST/work"; LOG="$DEST/local-pull.log"
log(){ echo "$(date -Is) $*" | tee -a "$LOG"; }
alert(){ [ -n "${ALERT_URL:-}" ] && curl -fsS -m 20 "$ALERT_URL" -H 'Content-Type: application/json' \
  -d "{\"subject\":\"home backup FAILED ($(hostname))\",\"text\":\"$(tail -n 30 "$LOG")\"}" || true; }
trap 'alert' ERR

if [ "${MODE:-cloud}" = cloud ]; then
  for r in $CLOUD_REMOTES; do
    rclone sync "$r" "$DEST/$(echo "$r" | cut -d: -f1)" || exit 1
  done
else
  for c in $DB_CONTAINER; do
    ssh -i "$SSH_KEY" "$VPS" "docker exec $c pg_dump --format=custom --no-acl --no-owner -U ${PGUSER:-postgres} ${DBNAME:-postgres}" > "$DEST/work/$c.dump" || exit 1
  done
  for v in $VOLUMES; do
    ssh -i "$SSH_KEY" "$VPS" "docker run --rm -v $v:/src:ro alpine tar czf - -C /src ." > "$DEST/work/$v.tgz" || exit 1
  done
fi

if [ -n "${LOCAL_REPO:-}" ]; then
  restic -r "$LOCAL_REPO" -p "$(cat ~/.deckhand-backup.pass)" backup "$DEST/work" --tag home >>"$LOG" 2>&1 || exit 1
  restic -r "$LOCAL_REPO" -p "$(cat ~/.deckhand-backup.pass)" forget --keep-last 3 --prune >>"$LOG" 2>&1 || exit 1
fi
log "pull OK (mode=$MODE)"
