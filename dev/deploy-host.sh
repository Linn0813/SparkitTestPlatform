#!/usr/bin/env bash
# 在部署机（Mac mini 等）上执行：启动 MySQL + MinIO，并创建 bucket
#
#   cd /path/to/SparkitTestPlatform/dev
#   chmod +x deploy-host.sh
#   ./deploy-host.sh
#
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -f .env.compose ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env.compose
  set +a
fi

MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASS="${MINIO_ROOT_PASSWORD:-minioadmin}"
BUCKET="${MINIO_BUCKET:-sparkit}"

echo "==> 启动测试平台中间件 sparkit-tp-mysql (3307) + sparkit-tp-minio (9000/9001)"
docker compose up -d

echo "==> 等待 MinIO..."
for i in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:9000/minio/health/live" >/dev/null 2>&1; then
    echo "MinIO 已就绪"
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "MinIO 启动超时" >&2
    exit 1
  fi
  sleep 2
done

echo "==> 等待 MySQL..."
for i in $(seq 1 30); do
  if docker compose exec -T mysql mysqladmin ping -h localhost -uroot -proot --silent 2>/dev/null; then
    echo "MySQL 已就绪"
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "MySQL 启动超时" >&2
    exit 1
  fi
  sleep 2
done

echo "==> 初始化 MinIO bucket: ${BUCKET}"
# minio/mc 镜像入口为 mc，需用 /bin/sh 执行多条命令
docker run --rm \
  --add-host=host.docker.internal:host-gateway \
  --entrypoint /bin/sh \
  minio/mc:latest \
  -c "mc alias set sparkit http://host.docker.internal:9000 '${MINIO_USER}' '${MINIO_PASS}' && mc mb --ignore-existing sparkit/${BUCKET}"

LAN_IP=""
if [[ "$(uname)" == "Darwin" ]]; then
  LAN_IP="$(ipconfig getifaddr en0 2>/dev/null || true)"
  [[ -z "$LAN_IP" ]] && LAN_IP="$(ipconfig getifaddr en1 2>/dev/null || true)"
fi

echo ""
echo "部署机中间件已启动（容器 sparkit-tp-mysql / sparkit-tp-minio）。"
echo "  MySQL:  127.0.0.1:3307  (sparkit / sparkit)"
echo "  MinIO:  API http://127.0.0.1:9000  控制台 http://127.0.0.1:9001"
echo "  账号:   ${MINIO_USER} / （见 dev/.env.compose 或默认 minioadmin）"
echo "  Bucket: ${BUCKET}"
if [[ -n "$LAN_IP" ]]; then
  echo ""
  echo "开发机 backend/.env 建议："
  echo "  DATABASE_URL=mysql+aiomysql://sparkit:sparkit@${LAN_IP}:3307/sparkit"
  echo "  MINIO_ENDPOINT=${LAN_IP}:9000"
  echo ""
  echo "或在开发机仓库根目录执行："
  echo "  ./dev/link-dev-to-deploy.sh ${LAN_IP}"
fi
echo ""
echo "请确保 macOS 防火墙允许入站：3307 (MySQL)、9000 (MinIO API)。"
