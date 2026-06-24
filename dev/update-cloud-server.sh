#!/usr/bin/env bash
# 在腾讯云 Linux 服务器上执行：拉代码、更新依赖、构建前端、重启服务。
#
#   cd ~/SparkitTestPlatform/dev
#   chmod +x update-cloud-server.sh
#   ./update-cloud-server.sh
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"

echo "==> 拉取最新代码"
git pull --ff-only origin main

echo "==> 更新后端依赖"
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

if command -v alembic >/dev/null 2>&1; then
  echo "==> 数据库迁移"
  alembic upgrade head
fi

echo "==> 构建前端"
cd "$ROOT/frontend"
npm install --silent
rm -f tsconfig.tsbuildinfo
npm run build

echo "==> 重启后端"
sudo systemctl restart sparkit-backend
sleep 3

echo "==> 重载 Nginx"
sudo nginx -t
sudo systemctl reload nginx

echo ""
echo "==> 健康检查（最多约 60 秒）"
HEALTH_OK=0
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null; then
    echo "后端正常: http://127.0.0.1:8000/health"
    HEALTH_OK=1
    break
  fi
  echo "  等待后端启动... (${i}/30)"
  sleep 2
done

if [[ $HEALTH_OK -ne 1 ]]; then
  echo "后端未响应，服务状态与最近日志:" >&2
  sudo systemctl status sparkit-backend --no-pager -l || true
  echo "" >&2
  sudo journalctl -u sparkit-backend -n 50 --no-pager || true
  ss -tlnp 2>/dev/null | grep -E ':8000|:3741' || true
  exit 1
fi

PUBLIC_URL=""
if [[ -f "$ROOT/backend/.env.local" ]]; then
  PUBLIC_URL="$(grep -E '^APP_PUBLIC_URL=' "$ROOT/backend/.env.local" | tail -1 | cut -d= -f2- || true)"
fi
echo ""
echo "更新完成。浏览器访问: ${PUBLIC_URL:-http://<公网IP>:3741}"
