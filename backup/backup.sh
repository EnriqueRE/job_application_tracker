#!/bin/sh
# Take one custom-format pg_dump into $BACKUP_DIR, then keep only the newest
# $BACKUP_KEEP dumps named tracker-*.dump. Other files in the directory are untouched.
#
# Connection settings come from libpq env vars (PGHOST, PGUSER, PGPASSWORD,
# PGDATABASE). Used by the Compose `backup` service, nightly and on demand:
#
#   docker compose exec backup /backup/backup.sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"

case "$BACKUP_KEEP" in
    '' | *[!0-9]* | 0)
        echo "backup: BACKUP_KEEP must be a positive integer, got '$BACKUP_KEEP'" >&2
        exit 2
        ;;
esac

name="tracker-$(date -u +%Y%m%dT%H%M%SZ).dump"
partial="$BACKUP_DIR/.$name.partial"

# Write to a hidden partial file and rename on success, so a failed or interrupted
# dump never looks like a good backup and never triggers pruning.
trap 'rm -f "$partial"' EXIT
pg_dump --format=custom >"$partial"
mv "$partial" "$BACKUP_DIR/$name"
trap - EXIT
echo "backup: wrote $BACKUP_DIR/$name"

# Names embed a UTC timestamp, so lexical order is chronological.
# shellcheck disable=SC2012
ls -1 "$BACKUP_DIR" | grep -E '^tracker-[0-9]{8}T[0-9]{6}Z\.dump$' | sort -r |
    tail -n +"$((BACKUP_KEEP + 1))" | while IFS= read -r old; do
    rm -f "$BACKUP_DIR/$old"
    echo "backup: pruned $BACKUP_DIR/$old"
done
