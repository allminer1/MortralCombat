#!/usr/bin/env bash
# Nightly database backup for the accounts feature (spec Section 8): pg_dump in custom
# format, 14 days kept. RUN ON THE SERVER, by cron, e.g. as root:
#
#     15 2 * * *  /home/AuE/neomortalsurv/deploy/backup.sh >> /var/log/neomortalsurv-backup.log 2>&1
#
# The dumps contain patient-level clinical inputs. They stay on this server, readable
# by root only. TODO(owner): an encrypted copy somewhere else.
#
# Restore (replaces the current contents; see docs/ACCOUNTS.md):
#     deploy/backup.sh --restore /var/backups/neomortalsurv/<file>.dump
set -euo pipefail

cd "$(dirname "$0")"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/neomortalsurv}"
KEEP_DAYS="${KEEP_DAYS:-14}"
COMPOSE=(docker compose)
if [[ -f .env ]]; then COMPOSE+=(--env-file .env); fi
COMPOSE+=(-f docker-compose.yml -f docker-compose.accounts.yml)
if [[ -n "${COMPOSE_EXTRA:-}" ]]; then
  # shellcheck disable=SC2206
  COMPOSE+=(${COMPOSE_EXTRA})
fi

if [[ "${1:-}" == "--restore" ]]; then
  file="${2:?usage: backup.sh --restore FILE}"
  [[ -f "$file" ]] || { echo "No such file: $file" >&2; exit 1; }
  echo "Restoring $file into the running database (current contents are replaced)."
  "${COMPOSE[@]}" exec -T db pg_restore -U neomortalsurv -d neomortalsurv --clean --if-exists --no-owner < "$file"
  echo "Restored."
  exit 0
fi

umask 077
mkdir -p "$BACKUP_DIR"
target="$BACKUP_DIR/neomortalsurv-$(date -u +%Y%m%dT%H%M%SZ).dump"
"${COMPOSE[@]}" exec -T db pg_dump -U neomortalsurv -d neomortalsurv -Fc > "$target.part"
# A dump that pg_restore cannot list is not a backup.
"${COMPOSE[@]}" exec -T db pg_restore --list < "$target.part" > /dev/null
mv "$target.part" "$target"
find "$BACKUP_DIR" -name 'neomortalsurv-*.dump' -mtime "+$KEEP_DAYS" -delete
echo "$(date -u +%FT%TZ) backup written: $target ($(du -h "$target" | cut -f1)); $(find "$BACKUP_DIR" -name 'neomortalsurv-*.dump' | wc -l | tr -d ' ') kept"
