# Jenkins 自动部署

push 到 `main` 后自动更新 **http://43.131.62.217:3741**。

## 两台服务器架构

| 机器 | IP | 角色 |
|------|-----|------|
| Jenkins | `49.51.186.145:8080` | 收到 Webhook，跑 Pipeline |
| 应用 | `43.131.62.217:3741` | MySQL/MinIO + 后端 + Nginx |

```text
GitHub push (main)
    ↓ Webhook
Jenkins (49.51.186.145)
    ↓ SSH ubuntu@43.131.62.217
dev/update-cloud-server.sh（在应用机上执行）
```

仓库根目录 **`Jenkinsfile`** 已通过 SSH 远程调用部署脚本。

---

## 一次性配置（必做）

### 1. 应用机 `43.131.62.217`

确认代码与脚本可用：

```bash
cd ~/SparkitTestPlatform/dev
chmod +x update-cloud-server.sh
./update-cloud-server.sh   # 手动跑通一次
```

### 2. Jenkins 机 `49.51.186.145` — 生成部署密钥

在 **Jenkins 所在机器**（或 Jenkins 容器内）执行：

```bash
ssh-keygen -t ed25519 -N "" -f ~/.jenkins_sparkit_tp_deploy -C "jenkins-sparkit-tp"
cat ~/.jenkins_sparkit_tp_deploy.pub
```

把输出的 **公钥** 追加到应用机：

```bash
# 在 43.131.62.217 上
echo 'ssh-ed25519 AAAA... jenkins-sparkit-tp' >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

在 **Jenkins 机** 测试：

```bash
ssh -i ~/.jenkins_sparkit_tp_deploy ubuntu@43.131.62.217 \
  'bash -lc "~/SparkitTestPlatform/dev/update-cloud-server.sh"'
```

### 3. Jenkins Web UI — 添加 SSH 凭据

1. **Manage Jenkins → Credentials → System → Global credentials → Add Credentials**
2. Kind: **SSH Username with private key**
3. ID: **`sparkit-tp-deploy-ssh`**（必须与 Jenkinsfile 一致）
4. Username: `ubuntu`
5. Private Key: Enter directly，粘贴 `~/.jenkins_sparkit_tp_deploy` 私钥全文
6. Save

### 4. Jenkins 任务 `dev-sparkit-testplatform`

- Pipeline from SCM → `SparkitTestPlatform` → branch `main` → Script Path `Jenkinsfile`
- 勾选 **GitHub hook trigger for GITScm polling**

### 5. GitHub Webhook

- URL: `http://49.51.186.145:8080/github-webhook/`
- Events: push

---

## 常见问题

### 构建 SUCCESS 但 Deploy skipped

旧版 Jenkinsfile 含 `when { branch 'main' }`，Pipeline 任务里分支名常匹配失败。已在新 Jenkinsfile 中移除，**push 最新 Jenkinsfile 后重新构建**。

### sshagent / credentials not found

- 安装插件 **SSH Agent Plugin**
- 凭据 ID 必须是 **`sparkit-tp-deploy-ssh`**

### Host key verification failed

Jenkinsfile 已加 `StrictHostKeyChecking=accept-new`；仍失败时在 Jenkins 机手动 ssh 一次应用机。

---

## 与 GitHub Actions 的关系

`.github/workflows/ci.yml` 里也有 push 部署 job，与 Jenkins **二选一**，避免重复部署。

---

## 手动触发 / 排错

```bash
# 应用机
cd ~/SparkitTestPlatform/dev && ./update-cloud-server.sh
sudo journalctl -u sparkit-backend -n 50 --no-pager
```

---

## 同机部署（Jenkins 与应用在同一台）

若以后合并到一台机器，可改 Jenkinsfile 为本地执行 `update-cloud-server.sh`，见 git 历史或 `install-jenkins-host.sh`。

---

## 文件说明

| 文件 | 用途 |
|------|------|
| `/Jenkinsfile` | SSH 远程部署 Pipeline |
| `dev/update-cloud-server.sh` | 在应用机上执行的部署步骤 |
| `dev/jenkins/docker-compose.yml` | Docker 跑 Jenkins（可选） |
