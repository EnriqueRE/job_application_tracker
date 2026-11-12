#!/bin/sh
# Entrypoint of the Compose `backup` service: run backup.sh every day at
# $BACKUP_TIME (HH:MM, in the container's timezone, UTC unless TZ is set).
# A failed backup is logged and retried at the next scheduled time.
set -eu

BACKUP_TIME="${BACKUP_TIME:-03:00}"
here="$(dirname "$0")"

# Fail fast on a malformed time instead of looping on an error.
date -d "$BACKUP_TIME" +%s >/dev/null

echo "backup: scheduled daily at $BACKUP_TIME ($(date +%Z)), keeping ${BACKUP_KEEP:-14} dumps"
while :; do
    now=$(date +%s)
    next=$(date -d "$BACKUP_TIME" +%s)
    if [ "$next" -le "$now" ]; then
        next=$((next + 86400))
    fi
    sleep "$((next - now))"
    "$here/backup.sh" || echo "backup: FAILED, will retry at next scheduled time" >&2
done
