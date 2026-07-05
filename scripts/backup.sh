#!/usr/bin/env bash
# Bundles everything you'd need to move FinAgent to another machine:
# the Postgres database (categories, merchants/rules, statements, transactions,
# chats) and the raw statement files in ./data.
#
# Qdrant's RAG index is NOT included on purpose — it's rebuilt automatically
# from the static knowledge files under backend/app/modules/tools/knowledge/
# the first time the agent uses rag_lookup, so there's nothing user-specific
# to carry over.
#
# Requires the postgres service from docker-compose.yml to be running
# (docker compose up -d postgres is enough, even if you run the backend
# itself outside Docker).
set -euo pipefail
cd "$(dirname "$0")/.."

STATEMENTS_DIR="${STATEMENTS_DIR:-./data}"
OUT="finagent-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"

echo "→ Dumping database via the postgres container..."
docker compose exec -T postgres pg_dump -U finagent -F c finagent > "$OUT/database.dump"

echo "→ Copying statement files from $STATEMENTS_DIR..."
cp -r "$STATEMENTS_DIR" "$OUT/data"

tar -czf "$OUT.tar.gz" "$OUT"
rm -rf "$OUT"

echo "✓ Backup written to $OUT.tar.gz"
echo "  Copy this file to the new machine and run: scripts/restore.sh $OUT.tar.gz"
