#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting local MySQL (port 3307)..."
docker compose up -d

echo "Waiting for MySQL..."
for i in $(seq 1 30); do
  if docker compose exec -T mysql mysqladmin ping -h localhost -uroot -proot --silent 2>/dev/null; then
    echo "MySQL is ready."
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "MySQL did not become ready in time." >&2
    exit 1
  fi
  sleep 2
done

echo "Done. MySQL sparkit @ 127.0.0.1:3307 (开发与部署共用此库)"
