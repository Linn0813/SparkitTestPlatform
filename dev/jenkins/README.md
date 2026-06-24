# Jenkins 自动部署

push 到 `main` 后自动更新 **http://43.131.62.217:3741**。

## 架构

```text
GitHub push (main)
    ↓ Webhook 或 Poll SCM
Jenkins（云服务器）
    ↓ 执行 Jenkinsfile
dev/update-cloud-server.sh
    ↓
git pull → 后端依赖 → alembic → npm build → systemd + Nginx
```

仓库根目录已有 **`Jenkinsfile`**，Pipeline 会调用 `update-cloud-server.sh`。

---

## 选型：两种装法

| | **A. 宿主机 apt 安装**（推荐） | **B. Docker 跑 Jenkins** |
|---|-------------------------------|---------------------------|
| 复杂度 | 低 | 中（需 SSH 回宿主机部署） |
| 端口 | 默认 **8080**（可改 8090） | **8090** |
| 部署脚本 | jenkins 用户 `sudo -u ubuntu` 跑脚本 | Pipeline 里 SSH `ubuntu@127.0.0.1` |
| 脚本 | `install-jenkins-host.sh` | `docker-compose.yml` |

**同一台机器上跑 Jenkins + Sparkit，优先用方案 A。**

---

## 方案 A：宿主机安装（推荐）

### 1. 安装 Jenkins

```bash
cd ~/SparkitTestPlatform/dev/jenkins
chmod +x install-jenkins-host.sh
sudo ./install-jenkins-host.sh
```

腾讯云安全组放行 Jenkins 端口（8080 或你改的 8090）。

### 2. 首次登录

```bash
sudo cat /var/lib/jenkins/secrets/initialAdminPassword
```

浏览器打开 `http://43.131.62.217:8080`，装推荐插件，创建管理员账号。

### 3. 创建 Pipeline 任务

1. **新建 Item** → 名称 `sparkit-deploy` → 类型 **Pipeline**
2. **Build Triggers**：
   - 勾选 **GitHub hook trigger for GITScm polling**（配 Webhook 后生效）
   - 或仅依赖 `Jenkinsfile` 里的 **Poll SCM**（约 2 分钟检查一次，无需 Webhook）
3. **Pipeline**：
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: `https://github.com/Linn0813/SparkitTestPlatform.git`
   - Credentials: 若私有库，添加 GitHub PAT
   - Branch: `*/main`
   - Script Path: `Jenkinsfile`

### 4. GitHub Webhook（push 即构建）

1. Jenkins 安装插件 **GitHub Integration** / **GitHub hook trigger**
2. Jenkins → 系统管理 → **GitHub** → 添加 Server（可选 PAT）
3. GitHub 仓库 → **Settings → Webhooks → Add webhook**
   - Payload URL: `http://43.131.62.217:8080/github-webhook/`（Docker 方案端口改为 8090）
   - Content type: `application/json`
   - Events: **Just the push event**
4. Push 一次到 `main`，看 Jenkins 是否自动构建

---

## 方案 B：Docker 安装 Jenkins

```bash
cd ~/SparkitTestPlatform/dev/jenkins
docker compose up -d
```

- UI: **http://43.131.62.217:8090**
- 安全组放行 **8090**
- Pipeline 需通过 **SSH** 在宿主机执行部署（容器内无法 `systemctl restart`）：

```groovy
sshagent(credentials: ['sparkit-deploy-ssh']) {
  sh 'ssh -o StrictHostKeyChecking=no ubuntu@172.17.0.1 "cd ~/SparkitTestPlatform/dev && ./update-cloud-server.sh"'
}
```

在 Jenkins 凭据里添加 `ubuntu` 的 SSH 私钥；`172.17.0.1` 为 Docker 默认网关（宿主机）。

---

## 与 GitHub Actions 的关系

仓库 `.github/workflows/ci.yml` 里已有 **push main 后 SSH 部署** 的 job。

若启用 Jenkins，建议 **二选一**，避免重复部署：

- 用 Jenkins → 删除或注释 `ci.yml` 里的 `deploy` job
- 用 GitHub Actions → 不必装 Jenkins

---

## 手动触发 / 排错

```bash
# 服务器上单独测部署脚本
cd ~/SparkitTestPlatform/dev
./update-cloud-server.sh

# Jenkins 日志（宿主机安装）
sudo journalctl -u jenkins -f

# 后端日志
sudo journalctl -u sparkit-backend -n 50 --no-pager
```

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `/Jenkinsfile` | Pipeline 定义 |
| `dev/update-cloud-server.sh` | 实际部署步骤 |
| `dev/jenkins/install-jenkins-host.sh` | 宿主机一键装 Jenkins |
| `dev/jenkins/docker-compose.yml` | Docker 方式装 Jenkins |
| `dev/jenkins/sudoers-jenkins-deploy` | sudo 权限示例 |
