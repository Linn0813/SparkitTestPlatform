#!/usr/bin/env bash
# 在部署机（公司 Mac，本机跑 MySQL + 前后端）上执行。
# 数据库/MinIO 仍用 127.0.0.1；对外访问地址写 Tailscale IP（同事内网 IP 可选加入 CORS）。
#
#   ./dev/configure-deploy-host-env.sh 100.122.228.39
#   ./dev/configure-deploy-host-env.sh 100.122.228.39 172.19.3.69
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/env-helpers.sh"

TAILSCALE_IP="${1:-}"
LAN_IP="${2:-}"

if [[ -z "$TAILSCALE_IP" ]]; then
  echo "用法: $0 <Tailscale_IP> [局域网_IP]" >&2
  echo "Tailscale IP 在菜单栏 Tailscale → 本机地址（100.x.x.x）" >&2
  exit 1
fi

ENV_FILE="$(ensure_backend_env "$ROOT")"

WEB_URL="http://${TAILSCALE_IP}:5174"
CORS="http://${TAILSCALE_IP}:5174,http://127.0.0.1:5174,http://localhost:5174"
if [[ -n "$LAN_IP" ]]; then
  CORS="${CORS},http://${LAN_IP}:5174"
fi

set_env_kv "$ENV_FILE" "DATABASE_URL" "mysql+aiomysql://sparkit:sparkit@127.0.0.1:3307/sparkit"
set_env_kv "$ENV_FILE" "DATABASE_HOST_LAN" ""
set_env_kv "$ENV_FILE" "DATABASE_HOST_WAN" ""
set_env_kv "$ENV_FILE" "MINIO_ENDPOINT" "127.0.0.1:9000"
set_env_kv "$ENV_FILE" "MINIO_ACCESS_KEY" "minioadmin"
set_env_kv "$ENV_FILE" "MINIO_SECRET_KEY" "minioadmin"
set_env_kv "$ENV_FILE" "MINIO_BUCKET" "sparkit"
set_env_kv "$ENV_FILE" "MINIO_SECURE" "false"
set_env_kv "$ENV_FILE" "APP_PUBLIC_URL" "$WEB_URL"
set_env_kv "$ENV_FILE" "API_PUBLIC_URL" "$WEB_URL"
set_env_kv "$ENV_FILE" "CORS_ORIGINS" "$CORS"

echo "已更新 backend/.env（部署机本机模式 + Tailscale 对外访问）："
echo "  DATABASE_URL=...@127.0.0.1:3307/..."
echo "  APP_PUBLIC_URL=${WEB_URL}"
echo "  API_PUBLIC_URL=${WEB_URL}"
echo "  CORS_ORIGINS=${CORS}"
echo ""
echo "下一步："
echo "  1. cd dev && ./deploy-host.sh"
echo "  2. ./dev/run-backend.sh 与 ./dev/run-frontend.sh"
echo "  3. 浏览器 http://${TAILSCALE_IP}:5174"
echo "  4. 项目设置 → 企微通知 → 站点访问地址 填 ${WEB_URL}"
echo "  5. 代码更新: cd dev && ./update-deploy.sh，然后重启前后端"
