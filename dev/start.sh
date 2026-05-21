#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 与 deploy-host.sh 相同；部署机请优先用 ./deploy-host.sh
exec "$SCRIPT_DIR/deploy-host.sh"
