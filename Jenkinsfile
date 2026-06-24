// SparkitTestPlatform — 云服务器自动部署
// Jenkins 与应用在同一个 ubuntu 服务器上时，Pipeline 直接调用 update-cloud-server.sh
//
// 触发方式（二选一）：
//   1. GitHub Webhook（推荐）— 见 dev/jenkins/README.md
//   2. Poll SCM — 下方 triggers 已启用备用轮询

pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    triggers {
        // push 后 Webhook 未到时，约每 2 分钟检查一次 main 是否有新提交
        pollSCM('H/2 * * * *')
    }

    stages {
        stage('Deploy') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                sh '''
                    set -euo pipefail
                    DEPLOY_SCRIPT="/home/ubuntu/SparkitTestPlatform/dev/update-cloud-server.sh"
                    if [[ ! -f "$DEPLOY_SCRIPT" ]]; then
                      echo "找不到部署脚本: $DEPLOY_SCRIPT" >&2
                      exit 1
                    fi
                    chmod +x "$DEPLOY_SCRIPT"
                    # 宿主机 apt 安装 Jenkins 时以 ubuntu 执行（见 dev/jenkins/sudoers-jenkins-deploy）
                    if id jenkins >/dev/null 2>&1 && [[ "$(whoami)" == "jenkins" ]]; then
                      sudo -u ubuntu "$DEPLOY_SCRIPT"
                    else
                      "$DEPLOY_SCRIPT"
                    fi
                '''
            }
        }
    }

    post {
        success {
            echo '✓ 部署成功 — http://43.131.62.217:3741'
        }
        failure {
            echo '✗ 部署失败 — 查看 Console Output 或服务器 journalctl -u sparkit-backend'
        }
    }
}
