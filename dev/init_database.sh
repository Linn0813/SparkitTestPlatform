#!/usr/bin/env bash
# 按 backend/.env 连接 MySQL：建库（若不存在）+ 建表 + 可选 seed
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ ! -d .venv ]]; then
  echo "请先创建虚拟环境：cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
  exit 1
fi
source .venv/bin/activate

if [[ ! -f .env.local ]]; then
  echo "缺少 backend/.env.local，请复制：cp backend/.env.production backend/.env.local"
  exit 1
fi

python scripts/init_database.py
python scripts/check_database.py
python "$ROOT/dev/seed.py"
echo "数据库初始化完成。"
