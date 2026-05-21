# SparkitTestPlatform 本地开发

应用**仅依赖 MySQL**（附件与图片也存库）。

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

脚本会：建库（若不存在）→ 建表 → `seed.py`（演示管理员，已存在则跳过）。

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
| 连不上 MySQL | Docker Desktop 是否运行；`docker ps` 是否有 `sparkit-mysql` |
| 端口 3307 占用 | 修改 `docker-compose.yml` 端口映射或释放占用 |
| 接口仍很慢 | 确认 `backend/.env` 未指向公网 IP；应为本机 `127.0.0.1:3307` |
| 登录失败 | 新库需 `./dev/init_database.sh` 或从备份导入用户表 |

## 清空 Docker 数据重来

```bash
docker compose down -v
./start.sh
./init_database.sh
```
