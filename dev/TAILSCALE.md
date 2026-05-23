# Tailscale 远程访问

两台设备登录**同一 Tailscale 账号**（喻晓玲）：

| 设备 | 用途 | Tailscale IP |
|------|------|----------------|
| multi-mediamac-mini | 部署机（MySQL + MinIO + 网站） | `100.122.228.39` |
| linns-macbook-pro | 开发机 | `100.118.205.93` |

IP 若变化，以 Tailscale 菜单显示为准。

> `backend/.env` **不要提交 Git**，用下面脚本在每台机器上各执行一次。

## 1. 部署机（multi-mediamac-mini，在公司 Mac 上）

```bash
cd SparkitTestPlatform/dev
chmod +x deploy-host.sh configure-deploy-host-env.sh
./deploy-host.sh
./configure-deploy-host-env.sh 100.122.228.39
# 若同事还要用局域网访问，加上局域网 IP（部署机 ipconfig getifaddr en0）：
# ./configure-deploy-host-env.sh 100.122.228.39 172.19.3.69
```

开两个终端：

```bash
./dev/run-backend.sh
./dev/run-frontend.sh
```

验证：浏览器打开 http://100.122.228.39:5174

**项目设置 → 企微通知 → 站点访问地址** 填：`http://100.122.228.39:5174`

## 2. 开发机（linns-macbook-pro，本地跑代码连远程库）

```bash
cd SparkitTestPlatform
./dev/link-dev-to-deploy.sh 100.122.228.39
./dev/run-backend.sh    # 终端 1
./dev/run-frontend.sh     # 终端 2
```

浏览器：http://127.0.0.1:5174（数据写在部署机 MySQL）

## 3. 只打开网页（不跑本地代码）

任意已登录 Tailscale 的设备访问：http://100.122.228.39:5174

## 注意

- 部署机保持开机，Docker + 前后端需运行。
- 同事在公司仍用局域网 `http://172.19.x.x:5174`，无需 Tailscale。
- 公司内网开发：`./dev/link-dev-to-deploy.sh 172.19.3.69`
