#!/usr/bin/env bash
# 从仓库任意位置启动后端（需先 ./start.sh 拉起 Docker）
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [[ ! -d .venv ]]; then
  echo "Creating venv..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

if [[ ! -f .env ]]; then
  cp "$ROOT/.env.example" .env
  echo "Created backend/.env from .env.example"
fi

# 首次或空库时执行：python scripts/init_database.py && python ../dev/seed.py

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
