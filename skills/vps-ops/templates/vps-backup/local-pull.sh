#!/usr/bin/env bash
# vps-ops HOME-side pull (ref 55 §7) — runs on the USER'S machine, NOT the VPS. LIVE-VERIFIED 2026-09-20.
# Mirrors the offsite buckets down to a local folder AND/OR a local RustFS S3 (Docker Desktop):
#   restic -r <DEST>/<provider>/coolify -p <pass> snapshots   (repos included — no server needed)
# Env file (chmod 600, LF only):
#   CLOUD_REMOTES="b2:my-bucket tigris:my-offsite-bucket"
#   DEST=C:/Users/<you>/deckhand-backups          # native path form — rclone is a native exe
#   LOCAL_S3_REMOTE=rustfs:<bucket>               # optional local RustFS target (templates/vps-backup/rustfs-local.compose.yml)
#   ALERT_URL=https://<app-domain>/api/mail-alert?secret=…   # optional; the route appends a link
# Schedule: cron / Windows Task Scheduler (.cmd wrapper) / an agent cronjob (Hermes needs its gateway).
set -euo pipefail
ENVF="${DECKHAND_ENV:-$HOME/.vps-ops/secrets/home-pull.env.sh}"
source "$ENVF"
DEST="${DEST:-$HOME/deckhand-backups}"; mkdir -p "$DEST"
LOG="$DEST/local-pull.log"; touch "$LOG"
log(){ echo "$(date -Is) $*" | tee -a "$LOG"; }
alert(){ [ -n "${ALERT_URL:-}" ] || return 0
  code=$(curl -sS -m 20 -o "$DEST/alert.out" -w '%{http_code}' "$ALERT_URL" -H 'Content-Type: application/json' \
    -d "{\"subject\":\"home backup FAILED ($(hostname))\",\"text\":\"$(tail -n 30 "$LOG" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr '\n' ' ')\"}") || code=000
  [ "$code" = 200 ] || log "ALERT DELIVERY http=$code"
}
trap 'alert' ERR

# preflight: S3 signing dies >15 min clock skew — warn BEFORE the first sync
date_hdr=$(curl -sI -m 10 https://t3.storage.dev 2>/dev/null | tr -d '\r' | sed -n 's/^[Dd]ate: //p' | head -1)
dateskew=$(date -u -d "$date_hdr" +%s 2>/dev/null || echo "")
if [ -n "$dateskew" ]; then
  skew=$(( $(date -u +%s) - dateskew ))
  if [ "${skew#-}" -gt 900 ]; then
    log "WARNING: PC clock skew ${skew}s (>15 min) — S3 signing will fail until fixed (Windows: w32tm /resync /force, elevated)"
  fi
fi

for r in $CLOUD_REMOTES; do
  prov=$(echo "$r" | cut -d: -f1)
  log "sync $r -> folder"
  rclone sync "$r" "$DEST/$prov" --transfers 4 --checkers 8 || exit 1
  if [ -n "${LOCAL_S3_REMOTE:-}" ]; then
    if rclone lsd "$LOCAL_S3_REMOTE" >/dev/null 2>&1; then
      log "sync $r -> $LOCAL_S3_REMOTE/$prov (local S3)"
      rclone sync "$r" "$LOCAL_S3_REMOTE/$prov" --transfers 4 --checkers 8 || exit 1
    else
      log "local S3 target '$LOCAL_S3_REMOTE' unreachable (Docker Desktop off / RustFS stopped?) — skipped, folder copy is intact"
    fi
  fi
done
log "pull OK"
