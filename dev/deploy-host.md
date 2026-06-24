# 部署机（Mac mini）安装 MySQL + MinIO

在**部署机**上克隆/拉取仓库后执行（只需一次，或升级后重跑）：

```bash
cd SparkitTestPlatform/dev
chmod +x deploy-host.sh
./deploy-host.sh
```

脚本会：

1. `docker compose up -d` 启动 MySQL（3307）与 MinIO（9000/9001）
2. 等待健康检查
3. 用 `minio/mc` 创建 bucket `sparkit`（默认名）

可选：改 MinIO 密码

```bash
cp .env.compose.example .env.compose
# 编辑 MINIO_ROOT_PASSWORD，须与开发机 backend/.env 中 MINIO_SECRET_KEY 一致
./deploy-host.sh
```

## 防火墙（macOS）

系统设置 → 网络 → 防火墙：允许 Docker 或放行 **3307**、**9000**（内网开发机访问）。

## 开发机连接部署机

在**你自己的电脑**（不要起第二套 Docker）：

```bash
./dev/link-dev-to-deploy.sh <部署机IP>
# 例：./dev/link-dev-to-deploy.sh 172.19.3.69
```

然后重启 `./dev/run-backend.sh`。附件与描述内图片经后端 `/api/v1/files/raw` 代理，**浏览器无需访问 MinIO 9000 端口**。

## Tailscale 远程（家里访问 / 笔记本连远程库）

详见 [TAILSCALE.md](TAILSCALE.md)。当前部署机 **multi-mediamac-mini** Tailscale IP：`100.122.228.39`

**部署机**（仅在公司 Mac 上执行一次）：

```bash
./dev/configure-deploy-host-env.sh 100.122.228.39
```

**开发机**（笔记本，本地跑代码连远程库）：

```bash
./dev/link-dev-to-deploy.sh 100.122.228.39
```

只打开网页：http://100.122.228.39:5174

## 控制台

- MinIO：http://\<部署机IP\>:9001（默认 `minioadmin` / `minioadmin`）
- 查看 bucket `sparkit` 内对象

## 代码更新

提交并 push 到远程后，在**部署机**上：

```bash
cd SparkitTestPlatform/dev
chmod +x update-deploy.sh   # 首次
./update-deploy.sh
```

按脚本提示重启 `./dev/run-backend.sh` 与 `./dev/run-frontend.sh`。
