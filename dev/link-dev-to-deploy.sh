#!/usr/bin/env bash
# 在开发机上执行：把 backend/.env 指向部署机的 MySQL + MinIO
#
#   ./dev/link-dev-to-deploy.sh 172.19.3.69
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"
EXAMPLE="$ROOT/.env.example"

DEPLOY_HOST="${1:-}"
if [[ -z "$DEPLOY_HOST" ]]; then
  echo "用法: $0 <部署机局域网 IP>" >&2
  echo "在部署机上查 IP: ipconfig getifaddr en0" >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$EXAMPLE" "$ENV_FILE"
  echo "已创建 backend/.env"
fi

_set_kv() {
  local key="$1"
  local val="$2"
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

DATABASE_URL="mysql+aiomysql://sparkit:sparkit@${DEPLOY_HOST}:3307/sparkit"
_set_kv "DATABASE_URL" "$DATABASE_URL"
_set_kv "MINIO_ENDPOINT" "${DEPLOY_HOST}:9000"
_set_kv "MINIO_ACCESS_KEY" "minioadmin"
_set_kv "MINIO_SECRET_KEY" "minioadmin"
_set_kv "MINIO_BUCKET" "sparkit"
_set_kv "MINIO_SECURE" "false"

echo "已更新 backend/.env："
echo "  DATABASE_URL=${DATABASE_URL}"
echo "  MINIO_ENDPOINT=${DEPLOY_HOST}:9000"
echo ""
echo "请确认部署机已执行: cd dev && ./deploy-host.sh"
echo "开发机不要执行 dev/start.sh，避免起第二套 Docker。"
