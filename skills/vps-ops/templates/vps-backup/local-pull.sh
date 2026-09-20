#!/usr/bin/env bash
# vps-ops HOME-side pull (ref 55 §7) — runs on the USER'S machine, NOT the VPS. LIVE-VERIFIED 2026-09-20.
# Choice ②: mirror the offsite buckets down — restic repos included, so a full local restore works:
#   restic -r <DEST>/<provider>/coolify -p <pass> snapshots   (no server needed)
# Choice ③ variant: swap the CLOUD_REMOTES loop for SSH pulls of fresh dumps (see README).
# Schedule it: cron / Windows Task Scheduler (wrap in a .cmd -> bash.exe -lc …) / a Hermes cronjob
# (needs the gateway running) / any agent with scheduling.
#
# Env file (chmod 600 — LF endings only):
#   CLOUD_REMOTES="b2:my-bucket tigris:my-offsite-bucket"
#   DEST=C:/Users/<you>/deckhand-backups      # native path form — rclone is a native exe
#   ALERT_URL=https://<app-domain>/api/mail-alert?secret=…   # optional; the route appends a link
# Windows gotchas: native exes want C:/… paths (not /c/…); if SigV4 says "Timestamp … is in the future",
# the PC clock drifted >15 min — start w32time + `w32tm /resync /force` (elevated), then retry.
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
for r in $CLOUD_REMOTES; do
  log "sync $r"
  rclone sync "$r" "$DEST/$(echo "$r" | cut -d: -f1)" --transfers 4 --checkers 8 || exit 1
done
log "pull OK"
