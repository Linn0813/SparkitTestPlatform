#!/usr/bin/env bash
# 在 Mac mini 部署机上执行：拉取最新代码并更新依赖。
# 云服务器请用 ./update-cloud-server.sh（见 deploy-cloud-server.md）
#
#   cd SparkitTestPlatform/dev
#   chmod +x update-deploy.sh
#   ./update-deploy.sh
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$ROOT"

echo "==> 拉取最新代码"
git pull --ff-only

echo "==> 更新后端依赖"
cd "$ROOT/backend"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

echo "==> 更新前端依赖"
cd "$ROOT/frontend"
npm install --silent

echo ""
echo "代码与依赖已更新。请重启前后端使改动生效："
echo ""
echo "  1. 在后端终端 Ctrl+C 停止，再执行: ./dev/run-backend.sh"
echo "  2. 在前端终端 Ctrl+C 停止，再执行: ./dev/run-frontend.sh"
echo ""
echo "若端口仍被占用，可先结束进程："
echo "  kill \$(lsof -t -i :8000) 2>/dev/null || true"
echo "  kill \$(lsof -t -i :5174) 2>/dev/null || true"
echo ""
echo "验证: http://100.122.228.39:5174 （或本机 Tailscale IP）"
