#!/usr/bin/env bash
# Nightly Postgres backup. Keeps 14 days locally; optionally copies to R2 via rclone.
# Cron: 17 2 * * * /opt/kwado/deploy/backup.sh >> /var/log/kwado-backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."
DIR=/var/backups/kwado
mkdir -p "$DIR"
FILE="$DIR/kwado-$(date +%Y%m%d-%H%M).sql.gz"
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U kwado -d kwado --no-owner | gzip > "$FILE"
find "$DIR" -name 'kwado-*.sql.gz' -mtime +14 -delete
if command -v rclone >/dev/null && rclone listremotes | grep -q '^r2:'; then
  rclone copy "$FILE" r2:kwado-backups/
fi
echo "$(date -Is) backup ok: $FILE"
