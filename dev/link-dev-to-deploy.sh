#!/usr/bin/env bash
# 在开发机（自己笔记本）上执行：backend 连部署机的 MySQL + MinIO。
# 部署机 IP 可以是公司局域网 IP，或 Tailscale 的 100.x.x.x。
#
#   ./dev/link-dev-to-deploy.sh 172.19.3.69
#   ./dev/link-dev-to-deploy.sh 100.122.228.39
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/env-helpers.sh"

DEPLOY_HOST="${1:-}"
if [[ -z "$DEPLOY_HOST" ]]; then
  echo "用法: $0 <部署机_IP>" >&2
  echo "  公司内网: ipconfig getifaddr en0（部署机上查）" >&2
  echo "  在家远程: 部署机 Tailscale 菜单里的 100.x.x.x" >&2
  exit 1
fi

ENV_FILE="$(ensure_backend_env "$ROOT")"

DATABASE_URL="mysql+aiomysql://sparkit:sparkit@${DEPLOY_HOST}:3307/sparkit"
set_env_kv "$ENV_FILE" "DATABASE_URL" "$DATABASE_URL"
set_env_kv "$ENV_FILE" "MINIO_ENDPOINT" "${DEPLOY_HOST}:9000"
set_env_kv "$ENV_FILE" "MINIO_ACCESS_KEY" "minioadmin"
set_env_kv "$ENV_FILE" "MINIO_SECRET_KEY" "minioadmin"
set_env_kv "$ENV_FILE" "MINIO_BUCKET" "sparkit"
set_env_kv "$ENV_FILE" "MINIO_SECURE" "false"
# 本地 dev：前端 5174 代理 /api，附件链接走相对路径
set_env_kv "$ENV_FILE" "APP_PUBLIC_URL" "http://127.0.0.1:5174"
set_env_kv "$ENV_FILE" "API_PUBLIC_URL" "http://127.0.0.1:8000"
set_env_kv "$ENV_FILE" "CORS_ORIGINS" "http://127.0.0.1:5174,http://localhost:5174"

echo "已更新 backend/.env（开发机连远程库）："
echo "  DATABASE_URL=${DATABASE_URL}"
echo "  MINIO_ENDPOINT=${DEPLOY_HOST}:9000"
echo ""
echo "请确认部署机已: cd dev && ./deploy-host.sh"
echo "开发机不要执行 dev/start.sh，避免起第二套 Docker。"
echo "然后在本机: ./dev/run-backend.sh 与 ./dev/run-frontend.sh"
