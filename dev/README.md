# SparkitTestPlatform 开发指南

业务数据在 **MySQL**，附件与视频在**腾讯云 COS**。

---

## 部署（云服务器）

项目部署在腾讯云 Linux 服务器，详见 [deploy-cloud-server.md](deploy-cloud-server.md)。

代码 push 后自动部署（Jenkins），或手动执行：

```bash
cd ~/SparkitTestPlatform/dev
./update-cloud-server.sh
```

---

## 本地开发（连云端数据库）

本地跑前后端代码，数据库连云服务器 MySQL（通过 SSH 隧道）。

### 1. 开启 SSH 隧道

```bash
# 需先配置 SSH 私钥
SSH_KEY=~/.sparkit_tp_deploy_pem ./dev/cloud-ssh-tunnel.sh 43.131.62.217
```

隧道开着时，`127.0.0.1:3307` → 云端 MySQL。

### 2. 配置 backend/.env.local

`backend/.env.local` 已配置指向 `127.0.0.1:3307`，隧道开启后直接可用。

### 3. 启动

**终端 1 — 后端：**

```bash
./dev/run-backend.sh
```

**终端 2 — 前端：**

```bash
./dev/run-frontend.sh
```

---

## 初始化数据库（首次或新库）

```bash
./dev/init_database.sh
```

---

## 排错

| 现象 | 处理 |
|------|------|
| 连不上 MySQL | 确认 SSH 隧道已开启；`curl -s http://127.0.0.1:8000/health` |
| 端口 3307 占用 | `lsof -ti :3307 \| xargs kill -9` 后重开隧道 |
| 登录失败 | 新库需 `./dev/init_database.sh` |
