#!/usr/bin/env bash
set -euo pipefail

DATA_DIR=${1:-./data}
BACKEND_URL=${BACKEND_URL:-http://localhost:8000}

for file in DAMGDAM.xlsx "DAM_Market Snapshot.xlsx" "GDAM_Market Snapshot.xlsx" "RTM_Market Snapshot.xlsx"; do
  if [ -f "$DATA_DIR/$file" ]; then
    echo "Ingesting $file"
    curl -sf -F "upload=@$DATA_DIR/$file" "$BACKEND_URL/api/ingest/file"
  else
    echo "Skipping $file - not found" >&2
  fi
done
