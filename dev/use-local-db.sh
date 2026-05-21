#!/usr/bin/env bash
# 启动 macOS 本地 Docker MySQL（部署库），并确保 backend/.env 指向同一 DATABASE_URL
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_DATABASE_URL="mysql+aiomysql://sparkit:sparkit@127.0.0.1:3307/sparkit"

echo "==> 启动部署用 MySQL（Docker，端口 3307，库 sparkit）"
"$SCRIPT_DIR/start.sh"

ENV_FILE="$ROOT/backend/.env"
EXAMPLE="$ROOT/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$EXAMPLE" "$ENV_FILE"
  echo "已创建 backend/.env（从 .env.example）"
fi

if grep -q '^DATABASE_URL=' "$ENV_FILE"; then
  if [[ "$(uname)" == "Darwin" ]]; then
    sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=${DEPLOY_DATABASE_URL}|" "$ENV_FILE"
  else
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=${DEPLOY_DATABASE_URL}|" "$ENV_FILE"
  fi
else
  echo "DATABASE_URL=${DEPLOY_DATABASE_URL}" >> "$ENV_FILE"
fi

echo ""
echo "backend/.env 已指向部署库："
echo "  ${DEPLOY_DATABASE_URL}"
echo ""
echo "下一步（空库或新环境）："
echo "  ./dev/init_database.sh"
echo "启动应用："
echo "  ./dev/run-backend.sh   # 终端 1"
echo "  ./dev/run-frontend.sh  # 终端 2"
