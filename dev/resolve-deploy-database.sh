#!/usr/bin/env bash
# 从 backend/.env 读取 DATABASE_HOST_LAN / DATABASE_HOST_WAN，按顺序探测 MySQL 端口，输出第一个可达的 host。
# 用法: ./dev/resolve-deploy-database.sh
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$ROOT/backend/.env"

read_env_var() {
  local key="$1"
  if [[ ! -f "$ENV_FILE" ]]; then
    return 1
  fi
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" 2>/dev/null | tail -1 || true)"
  [[ -n "$line" ]] || return 1
  local val="${line#*=}"
  val="${val%\"}"
  val="${val#\"}"
  val="${val%\'}"
  val="${val#\'}"
  printf '%s' "$val"
}

can_connect() {
  local host="$1"
  local port="$2"
  if [[ -z "$host" ]]; then
    return 1
  fi
  if command -v nc >/dev/null 2>&1; then
    if nc -z -w 2 "$host" "$port" 2>/dev/null; then
      return 0
    fi
    if nc -z -G 2 "$host" "$port" 2>/dev/null; then
      return 0
    fi
  fi
  if bash -c "exec 3<>/dev/tcp/${host}/${port}" 2>/dev/null; then
    bash -c "exec 3<&-; exec 3>&-" 2>/dev/null || true
    return 0
  fi
  return 1
}

PORT="$(read_env_var DATABASE_PORT || true)"
PORT="${PORT:-3307}"

LAN="$(read_env_var DATABASE_HOST_LAN || true)"
WAN="$(read_env_var DATABASE_HOST_WAN || true)"

if [[ -z "$LAN" && -z "$WAN" ]]; then
  echo "未配置 DATABASE_HOST_LAN / DATABASE_HOST_WAN（见 backend/.env）" >&2
  echo "开发机连远程库请先执行: ./dev/link-dev-to-deploy.sh <内网IP> [外网IP]" >&2
  exit 1
fi

for host in "$LAN" "$WAN"; do
  if [[ -z "$host" ]]; then
    continue
  fi
  if can_connect "$host" "$PORT"; then
    echo "$host"
    exit 0
  fi
  echo "不可达: ${host}:${PORT}" >&2
done

echo "无法连接部署机 MySQL（已尝试内网与外网地址，端口 ${PORT}）" >&2
echo "请确认部署机已执行: cd dev && ./deploy-host.sh" >&2
exit 1
