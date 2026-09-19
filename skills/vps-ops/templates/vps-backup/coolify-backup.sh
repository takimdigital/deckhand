#!/usr/bin/env bash
# vps-ops deep backup layer (ref 55 §5) — restic → TWO offsite S3 providers.
# Backs up: every Coolify DB container (incl. coolify-db, logical dumps) + an explicit app-volume allowlist.
# Install on the VPS: restic (static binary), jq, docker. Secrets under /etc/backup (root, 600).
# cron: 15 3 * * *  /opt/backup/coolify-backup.sh backup
#       30 4 * * 0  /opt/backup/coolify-backup.sh verify
# ADAPT: fill /etc/backup/env (below), PIN your volume allowlist, escrow restic-*.pass OFF this box.
# [verify at live drill — this template has not been exercised end-to-end yet]
#
# /etc/backup/env (root, 600):
#   R2_ACCOUNT_ID=…  R2_BUCKET=…  B2_HOST=s3.us-west-004.backblazeb2.com  B2_BUCKET=…
#   ALERT_URL=https://<app-domain>/api/mail-alert        # guarded route -> mail chain (ref 70)
#   VOLUMES="rustfs-data myapp-uploads"                  # explicit allowlist, space-separated
#   DB_CONTAINERS="<db-uuid> coolify-db"                 # container name = uuid (ref 50 §5)
#   PGUSER=postgres  DBNAME=postgres
set -euo pipefail
source /etc/backup/env
R2PASS=/etc/backup/restic-r2.pass; B2PASS=/etc/backup/restic-b2.pass   # 600 root; ALSO escrow off-box
R2="s3:https://${R2_ACCOUNT_ID}.r2.cloudflarestorage.com/${R2_BUCKET}/coolify"
B2="s3:${B2_HOST}/${B2_BUCKET}/coolify"
STAGE=/var/tmp/coolify-backup; STATE=/opt/backup/state; LOG=/var/log/coolify-backup.log
mkdir -p "$STATE"
log(){ echo "$(date -Is) $*" | tee -a "$LOG"; }
alert(){ curl -fsS -m 20 "$ALERT_URL" -H 'Content-Type: application/json' \
  -d "$(jq -nc --arg s "$1" --arg b "$2" '{subject:$s,text:$b}')" || log "ALERT DELIVERY FAILED"; }
state(){ echo "{\"status\":\"$1\",\"step\":\"$2\",\"ts\":\"$(date -Is)\"}" > "$STATE/status.json"; }
die(){ state failed "$1"; alert "backup FAILED on $(hostname): $1" "$(tail -n 40 "$LOG")"; exit 1; }

backup(){
  rm -rf "$STAGE"; mkdir -p "$STAGE/pg" "$STAGE/volumes"; trap 'rm -rf "$STAGE"' EXIT
  for c in $DB_CONTAINERS; do
    docker exec "$c" pg_dump --format=custom --no-acl --no-owner -U "${PGUSER:-postgres}" \
      "${DBNAME:-postgres}" > "$STAGE/pg/$c.dump" || die "pg_dump $c"
  done
  for v in $VOLUMES; do
    docker run --rm -v "$v":/src:ro -v "$STAGE/volumes":/out alpine tar czf "/out/$v.tgz" -C /src . \
      || die "tar $v"
  done
  restic -r "$R2" -p "$R2PASS" backup "$STAGE" --tag daily --host coolify-vps || die "restic backup R2"
  restic -r "$B2" -p "$B2PASS" backup "$STAGE" --tag daily --host coolify-vps || die "restic backup B2"
  restic -r "$R2" -p "$R2PASS" forget --keep-last 3 --prune || die "prune R2"
  restic -r "$B2" -p "$B2PASS" forget --keep-last 3 --prune || die "prune B2"
  state ok backup; log "backup OK"   # success is silent; the weekly verify sends the heartbeat
}

verify(){ # weekly drill: freshness + sampled bytes on BOTH repos + functional restore from R2
  rc=0
  for pair in "$R2 $R2PASS" "$B2 $B2PASS"; do set -- $pair
    restic -r "$1" -p "$2" snapshots --latest 1 --json >>"$LOG" || rc=1
    restic -r "$1" -p "$2" check --read-data-subset=10% >>"$LOG" || rc=1   # plain check reads NO data
    t=$(restic -r "$1" -p "$2" snapshots --latest 1 --json | jq -r '.[0].time')
    age=$(( ($(date -u +%s) - $(date -u -d "$t" +%s)) / 3600 ))
    [ "$age" -lt 26 ] || { log "stale snapshot in $1 ($age h)"; rc=1; }
  done
  # monthly: repeat the restore block against $B2 (egress stays in B2's 3x free allowance)
  restic -r "$R2" -p "$R2PASS" restore latest --target /var/tmp/drill --include "$STAGE/pg" || rc=1
  dump=$(ls /var/tmp/drill"$STAGE"/pg/*.dump | head -1)
  pg_restore -l "$dump" >/dev/null || rc=1              # TOC intact
  docker rm -f drill-pg 2>/dev/null || true
  docker run -d --name drill-pg -e POSTGRES_PASSWORD=drill postgres:16 >/dev/null || rc=1
  for i in $(seq 30); do docker exec drill-pg pg_isready -U postgres -q && break; sleep 2; done
  docker exec drill-pg createdb -U postgres drill || rc=1
  docker exec -i drill-pg pg_restore -U postgres -d drill --no-owner --no-acl < "$dump" || rc=1
  docker exec drill-pg psql -U postgres -d drill -tAc 'select count(*) from users' || rc=1  # real query
  docker rm -f drill-pg >/dev/null; rm -rf /var/tmp/drill
  if [ $rc -eq 0 ]; then state ok verify; alert "restore drill PASS" "latest R2+B2 snapshots verified $(date -Is)"
  else state failed verify; alert "restore drill FAILED on $(hostname)" "$(tail -n 60 "$LOG")"; fi
  exit $rc
}
case "${1:-backup}" in backup) backup;; verify) verify;; *) echo "usage: $0 backup|verify"; exit 2;; esac
