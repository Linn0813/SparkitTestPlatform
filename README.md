# SparkitTestPlatform

轻量测试管理平台（Python FastAPI + Vue3），**仅需 MySQL**：业务数据与附件/图片均存入数据库，表结构由 `backend/scripts/init_database.py` 初始化。

## 功能

- 用户登录 / JWT、项目 / 成员与角色（member / tester / project_admin）
- **工作台**：KPI 概览、版本/缺陷/计划统计图；按角色展示待办（成员：跟进缺陷；测试：计划与待验证缺陷）
- **需求 / 版本**：需求管理、版本详情（关联需求与规划缺陷）
- **测试用例**：模块树、步骤表格式 CRUD、导入
- **测试计划**：关联用例、计划内执行、通过率、相关缺陷
- **缺陷管理**：跟进人、CRUD、关联需求/计划、附件（存 MySQL）
- **项目设置**：可编辑用例/缺陷字段模板、缺陷状态、企业微信 Webhook 通知

详见 [docs/MVP.md](docs/MVP.md)。

## 快速开始（macOS + Docker MySQL）

**开发与部署共用同一数据库**：在 Mac 上用 Docker 跑 MySQL，本地调试后端时也连这个库（`127.0.0.1:3307` / `sparkit`），不要单独再配一套「仅开发用」的远程库。

### 1. 准备数据库

安装 [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) 后：

```bash
cd dev
chmod +x use-local-db.sh   # 首次
./use-local-db.sh            # 启动 MySQL + 配置 backend/.env
./init_database.sh         # 空库时：建表 + 演示账号
```

### 2. 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# .env 已由 use-local-db.sh 写好；也可：cp ../.env.example .env
cd .. && ./dev/run-backend.sh
```

API 文档：http://localhost:8000/docs

默认管理员（seed 创建）：

- 邮箱：`admin@example.com`
- 密码：`Admin123!`（首次登录后请修改）

### 3. 前端

```bash
cd frontend
npm install
npm run dev    # http://localhost:5174
```

### 4. 从云服务器迁库（可选）

若之前使用公网 MySQL，见 [dev/migrate-remote-to-local.md](dev/migrate-remote-to-local.md)。

### 5. 企微通知

在 **项目设置 → 企微通知** 填入群机器人 Webhook URL，并在 **缺陷状态** 中勾选需要通知的状态。

### 6. 停止 MySQL

```bash
cd dev && ./stop.sh
```

## 配置说明

| 文件 | 说明 |
|------|------|
| `backend/.env` | **勿提交 Git**。`DATABASE_URL` 开发与部署一致 |
| `.env.example` | 模板，默认 `127.0.0.1:3307/sparkit` |

部署到本机其它进程（如 systemd 跑 uvicorn）时，同样使用上述 `DATABASE_URL`，保证与本地 `run-backend.sh` 访问同一库。

### 在自己电脑开发、数据库在另一台 Mac 上

`backend/.env` 使用部署机 IP，例如：

`DATABASE_URL=mysql+aiomysql://sparkit:sparkit@172.19.3.69:3307/sparkit`

详见 [dev/README.md](dev/README.md)「在自己电脑开发、连部署机数据库」。

## 性能

MySQL 与后端同在 Mac 本机时，接口延迟远低于公网远程库。若仍慢，检查 `DATABASE_URL` 是否误指向外网 IP。连接池说明见 `GET /health` 的 `db_pool` 字段。

## 端口（避免与 MeterSphere 冲突）

| 服务 | 端口 |
|------|------|
| 后端 API | 8000 |
| 前端 | 5174 |
| MySQL（Docker） | 3307 |

## 目录

```
SparkitTestPlatform/
├── backend/     # FastAPI
├── frontend/    # Vue3
├── docs/        # MVP 范围说明
└── dev/         # Docker Compose、seed、部署库脚本
```

详细说明见 [dev/README.md](dev/README.md)。

cd /Users/linnlingling/SparkitTestPlatform
./dev/run-backend.sh          # 终端 1，读 172.19.3.69 的库
cd frontend && npm run dev 
