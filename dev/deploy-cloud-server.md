# 云服务器部署与更新

适用于 **Linux 云服务器**（如腾讯云 `ubuntu@43.131.62.217`），架构：

| 组件 | 方式 | 端口 |
|------|------|------|
| MySQL | Docker `sparkit-tp-mysql` | 3307（仅本机） |
| 文件存储 | 腾讯云 COS | — |
| 后端 FastAPI | systemd `sparkit-backend` | 8000（仅本机） |
| 前端 Vue | `npm run build` + Nginx | **3741**（对外） |

访问地址：**http://43.131.62.217:3741**

---

## 首次部署

详见历史对话或按顺序执行：初始化 MySQL → 配置 `backend/.env.local` → systemd → Nginx。

---

## 代码更新（提交 push 后）

### Jenkins 自动部署（推荐）

push 到 `main` 后由 Jenkins 执行 `Jenkinsfile` → `update-cloud-server.sh`。

配置步骤见 **[dev/jenkins/README.md](jenkins/README.md)**。

### 手动更新

```bash
cd ~/SparkitTestPlatform/dev
chmod +x update-cloud-server.sh   # 首次
./update-cloud-server.sh
```

脚本会：`git pull` → 装 Python 依赖 → `alembic upgrade head` → `npm run build` → 重启 `sparkit-backend` → 重载 Nginx。

### 手动更新（不用脚本时）

```bash
cd ~/SparkitTestPlatform
git pull origin main

cd backend && source .venv/bin/activate
pip install -q -r requirements.txt
alembic upgrade head

cd ../frontend
npm install
npm run build

sudo systemctl restart sparkit-backend
sudo nginx -t && sudo systemctl reload nginx
curl -s http://127.0.0.1:8000/health
```

### 验证

浏览器打开 http://43.131.62.217:3741 ，确认功能正常。

### 排错

```bash
sudo systemctl status sparkit-backend --no-pager
sudo journalctl -u sparkit-backend -n 50 --no-pager
ss -tlnp | grep -E ':3741|:8000'
```
