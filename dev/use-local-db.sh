#!/usr/bin/env bash
# 启动 macOS 本地 Docker MySQL（部署库），并确保 backend/.env 指向同一 DATABASE_URL
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_DATABASE_URL="mysql+aiomysql://sparkit:sparkit@127.0.0.1:3307/sparkit"
MINIO_ENDPOINT="127.0.0.1:9000"

echo "==> 启动部署用 MySQL + MinIO（本机 Docker）"
"$SCRIPT_DIR/deploy-host.sh"

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

_set_kv() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE"; then
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    else
      sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
    fi
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

_set_kv "MINIO_ENDPOINT" "$MINIO_ENDPOINT"
_set_kv "MINIO_ACCESS_KEY" "minioadmin"
_set_kv "MINIO_SECRET_KEY" "minioadmin"
_set_kv "MINIO_BUCKET" "sparkit"
_set_kv "MINIO_SECURE" "false"

echo ""
echo "backend/.env 已指向本机部署中间件："
echo "  ${DEPLOY_DATABASE_URL}"
echo "  MINIO_ENDPOINT=${MINIO_ENDPOINT}"
echo ""
echo "下一步（空库或新环境）："
echo "  ./dev/init_database.sh"
echo "启动应用："
echo "  ./dev/run-backend.sh   # 终端 1"
echo "  ./dev/run-frontend.sh  # 终端 2"
