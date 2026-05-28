#!/usr/bin/env bash
# 从仓库任意位置启动后端（需先 ./start.sh 拉起 Docker）
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT/backend"

if [[ ! -d .venv ]]; then
  echo "Creating venv..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

if [[ ! -f .env ]]; then
  cp "$ROOT/.env.example" .env
  echo "Created backend/.env from .env.example"
fi

# 首次或空库时执行：python scripts/init_database.py && python ../dev/seed.py

ENV_FILE="$ROOT/backend/.env"
if [[ -f "$ENV_FILE" ]]; then
  # 部署机本机库：DATABASE_URL 指向 127.0.0.1 / localhost，不做内网外网探测
  if grep -qE '^DATABASE_URL=.*@(127\.0\.0\.1|localhost)[:/]' "$ENV_FILE" 2>/dev/null; then
    :
  elif grep -qE '^DATABASE_HOST_(LAN|WAN)=[^[:space:]]' "$ENV_FILE" 2>/dev/null; then
    # 仅开发机连远程部署库：按 LAN → WAN 探测后注入连接串
    DEPLOY_HOST="$("$DEV_DIR/resolve-deploy-database.sh")"
    DB_PORT="$(grep -E '^DATABASE_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || echo 3307)"
    DB_PORT="${DB_PORT:-3307}"
    export DATABASE_URL="mysql+aiomysql://sparkit:sparkit@${DEPLOY_HOST}:${DB_PORT}/sparkit"
    export MINIO_ENDPOINT="${DEPLOY_HOST}:9000"
    echo "Using deploy host: ${DEPLOY_HOST} (database + MinIO)"
  elif grep -qE '^DATABASE_URL=.*@(1[0-9]{2}\.|172\.|100\.)' "$ENV_FILE" 2>/dev/null; then
    echo "提示: 开发机连远程库建议配置内网/外网双地址:" >&2
    echo "  ./dev/link-dev-to-deploy.sh <内网IP> [外网/Tailscale_IP]" >&2
    echo "部署机请用 127.0.0.1: ./dev/configure-deploy-host-env.sh <Tailscale_IP>" >&2
  fi
fi

PORT=8000
if lsof -i ":$PORT" -sTCP:LISTEN -t >/dev/null 2>&1; then
  if curl -sf "http://127.0.0.1:$PORT/health" >/dev/null; then
    echo "Backend already running on http://127.0.0.1:$PORT (stop it first: kill \$(lsof -t -i :$PORT))"
    exit 0
  fi
  echo "Port $PORT is in use but /health failed. Free the port: kill \$(lsof -t -i :$PORT)" >&2
  exit 1
fi

echo "Starting API http://127.0.0.1:$PORT (docs: /docs)"
exec uvicorn app.main:app --reload --host 0.0.0.0 --port "$PORT"
