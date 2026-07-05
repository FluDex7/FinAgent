#!/usr/bin/env bash
# Restores a backup produced by scripts/backup.sh onto a fresh FinAgent
# checkout. Existing database contents are replaced; run this before you've
# started using the new machine for real, or after backing up again.
#
# Requires the postgres service from docker-compose.yml to be running
# (docker compose up -d postgres is enough, even if you run the backend
# itself outside Docker).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ $# -ne 1 ]; then
  echo "Usage: $0 <finagent-backup-*.tar.gz>" >&2
  exit 1
fi

ARCHIVE="$1"
STATEMENTS_DIR="${STATEMENTS_DIR:-./data}"
WORKDIR=$(mktemp -d)
trap 'rm -rf "$WORKDIR"' EXIT

tar -xzf "$ARCHIVE" -C "$WORKDIR"
BUNDLE_DIR=$(find "$WORKDIR" -maxdepth 1 -mindepth 1 -type d)

echo "→ Restoring database via the postgres container (existing data will be replaced)..."
docker compose exec -T postgres pg_restore -U finagent --clean --if-exists -d finagent < "$BUNDLE_DIR/database.dump"

echo "→ Restoring statement files into $STATEMENTS_DIR..."
mkdir -p "$STATEMENTS_DIR"
cp -r "$BUNDLE_DIR/data/." "$STATEMENTS_DIR/"

echo "✓ Restore complete. Start FinAgent normally — Qdrant's RAG index rebuilds itself on first use."
