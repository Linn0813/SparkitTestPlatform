#!/usr/bin/env bash
# 在云服务器上以 apt 安装 Jenkins（与 Sparkit 同机部署时推荐）
#
#   cd SparkitTestPlatform/dev/jenkins
#   chmod +x install-jenkins-host.sh
#   sudo ./install-jenkins-host.sh
#
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
  echo "请使用 sudo 运行: sudo $0" >&2
  exit 1
fi

echo "==> 添加 Jenkins 官方源"
install -d -m 0755 /etc/apt/keyrings
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2023.key \
  | tee /usr/share/keyrings/jenkins-keyring.asc >/dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] https://pkg.jenkins.io/debian-stable binary/" \
  | tee /etc/apt/sources.list.d/jenkins.list >/dev/null

echo "==> 安装 Jenkins + Java"
apt-get update
apt-get install -y fontconfig openjdk-17-jre jenkins

echo "==> 允许 jenkins 以 ubuntu 执行部署脚本"
DEPLOY_SCRIPT="/home/ubuntu/SparkitTestPlatform/dev/update-cloud-server.sh"
cat >/etc/sudoers.d/jenkins-sparkit-deploy <<EOF
jenkins ALL=(ubuntu) NOPASSWD: ${DEPLOY_SCRIPT}
EOF
chmod 440 /etc/sudoers.d/jenkins-sparkit-deploy

echo "==> 启动 Jenkins"
systemctl enable --now jenkins

echo ""
echo "Jenkins 已安装。"
echo "  初始管理员密码: sudo cat /var/lib/jenkins/secrets/initialAdminPassword"
echo "  Web UI: http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "若 8080 已被占用，可改 /etc/default/jenkins 中 HTTP_PORT 为 8090 后 systemctl restart jenkins"
echo "下一步: 见 dev/jenkins/README.md 创建 Pipeline 任务"
