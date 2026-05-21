# 从云服务器 MySQL 迁到 macOS 部署库

部署库与开发库为**同一实例**：`127.0.0.1:3307` / 库名 `sparkit`（`dev/docker-compose.yml`）。

## 1. 启动本地部署 MySQL

```bash
cd dev
./use-local-db.sh
```

## 2. 从旧环境导出（在云机器或能访问旧库的机器执行）

勿将密码写入仓库。示例（按你的旧库修改主机、用户、库名）：

```bash
mysqldump -h OLD_HOST -u root -p --single-transaction --routines --triggers sparkit > sparkit_backup.sql
```

## 3. 导入 macOS Docker 库

确保容器已启动（`docker ps` 可见 `sparkit-mysql`）：

```bash
mysql -h 127.0.0.1 -P 3307 -u sparkit -psparkit sparkit < sparkit_backup.sql
```

若 dump 内含 `CREATE DATABASE`，可先编辑去掉建库语句，或导入前：

```bash
mysql -h 127.0.0.1 -P 3307 -u sparkit -psparkit -e "CREATE DATABASE IF NOT EXISTS sparkit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

## 4. 校验

```bash
cd backend && source .venv/bin/activate
python scripts/check_database.py
```

## 5. 应用配置

`backend/.env` 中 `DATABASE_URL` 应为：

`mysql+aiomysql://sparkit:sparkit@127.0.0.1:3307/sparkit`

开发与本地跑的后端都使用该配置，即连接部署库。

## 从 `sparkit_test` 旧 Docker 卷迁移

若你曾用库名 `sparkit_test`，可只导数据：

```bash
mysqldump -h 127.0.0.1 -P 3307 -u sparkit -psparkit sparkit_test > from_test.sql
# 编辑 from_test.sql 将 sparkit_test 改为 sparkit（或导入后 rename）
mysql -h 127.0.0.1 -P 3307 -u sparkit -psparkit sparkit < from_test.sql
```
