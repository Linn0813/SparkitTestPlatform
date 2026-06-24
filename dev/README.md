# SparkitTestPlatform 本地开发

业务数据在 **MySQL**，附件与视频在 **MinIO**（`dev/docker-compose.yml` 一并启动）。

## 部署机安装 MySQL + MinIO

在 **Mac mini（部署机）** 上进入仓库 `dev` 目录，执行一次：

```bash
./deploy-host.sh
```

详见 [deploy-host.md](deploy-host.md)。

## 部署机更新代码

### Mac mini（公司内网 / Tailscale）

代码 push 到远程后：

```bash
cd SparkitTestPlatform/dev
./update-deploy.sh
```

然后重启 `./dev/run-backend.sh` 与 `./dev/run-frontend.sh`。

### 云服务器（腾讯云）

见 [deploy-cloud-server.md](deploy-cloud-server.md)，执行：

```bash
cd ~/SparkitTestPlatform/dev
./update-cloud-server.sh
```

## 在自己电脑开发、连部署机数据库

**部署机（Mac mini）** 用本机 `127.0.0.1` 连 Docker MySQL，不要配 `DATABASE_HOST_LAN/WAN`。首次可执行 `./dev/configure-deploy-host-env.sh <Tailscale_IP>`，再 `./dev/run-backend.sh`。

在你**开发机（笔记本）**上：

1. 查部署机局域网 IP（在 Mac mini 上）：`ipconfig getifaddr en0`；外网可用 Tailscale `100.x.x.x`
2. 配置远程库（内网优先，启动时自动探测可达地址）：

```bash
./dev/link-dev-to-deploy.sh <内网IP> [外网IP]
# 例: ./dev/link-dev-to-deploy.sh 172.19.3.69 100.122.228.39
```

会在 `backend/.env` 写入 `DATABASE_HOST_LAN` / `DATABASE_HOST_WAN`；`./dev/run-backend.sh` 启动时再注入 `DATABASE_URL`。

3. **不要**在开发机执行 `dev/start.sh`（除非你想用本机独立库）
4. 验证：`cd backend && source .venv/bin/activate && python scripts/check_database.py`（需先启动后端或临时 export DATABASE_URL）
5. 本机启动：`./dev/run-backend.sh` + `frontend` 里 `npm run dev`

部署机防火墙需允许 **3307** 入站（仅内网）。后端、前端进程在开发机跑，数据在部署机 MySQL。

---

## 数据库：开发与部署共用

在 macOS 上用 Docker 跑 MySQL，**开发环境 `backend/.env` 与部署环境使用同一个 `DATABASE_URL`**，避免两套库数据不一致。

| 项 | 值 |
|----|-----|
| 地址 | `127.0.0.1:3307`（映射容器 3306） |
| 库名 | `sparkit` |
| 用户 / 密码 | `sparkit` / `sparkit` |
| 连接串 | `mysql+aiomysql://sparkit:sparkit@127.0.0.1:3307/sparkit` |

### 一键准备

```bash
chmod +x use-local-db.sh   # 首次
./use-local-db.sh          # 启动 Docker MySQL + 写入 backend/.env
```

### 手动启动中间件

```bash
./start.sh   # 启动
./stop.sh    # 停止（保留 volume 数据）
```

需已安装并运行 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)。

## 初始化数据库

`backend/.env` 指向上述 `DATABASE_URL` 后，在仓库根目录：

```bash
./dev/init_database.sh
```

脚本会：探测业务库 → 若不存在则用 **root** 建库（`sparkit` 用户无权访问 `mysql` 系统库）→ 建表 → `seed.py`。

若 `init_database` 报 `Access denied ... to database 'mysql'`，先 `git pull` 最新代码；或在该机执行：`cd backend && source .venv/bin/activate && python scripts/init_database.py`（已修复为先连 `sparkit` 库、建库用 root）。

从云服务器迁数据见 [migrate-remote-to-local.md](migrate-remote-to-local.md)。

## 启动应用

**终端 1 — 后端：**

```bash
./dev/run-backend.sh
```

**终端 2 — 前端：**

```bash
./dev/run-frontend.sh
```

## 排错

| 现象 | 处理 |
|------|------|
| 连不上 MySQL | Docker Desktop 是否运行；`docker ps` 是否有 `sparkit-tp-mysql` |
| 端口 3307 占用 | 修改 `docker-compose.yml` 端口映射或释放占用 |
| 接口仍很慢 | 在公司内网应优先连 `DATABASE_HOST_LAN`；见启动日志 `Using deploy host:` |
| 启动报连不上 MySQL | 配置 `DATABASE_HOST_LAN`/`WAN` 后重跑；确认部署机 `./deploy-host.sh` 已运行 |
| 登录失败 | 新库需 `./dev/init_database.sh` 或从备份导入用户表 |

## 清空 Docker 数据重来

```bash
docker compose down -v
./start.sh
./init_database.sh
```
