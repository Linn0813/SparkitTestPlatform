// SparkitTestPlatform — 测试管理平台（Python + Vue）
// Jenkins: 49.51.186.145  --SSH-->  应用: 43.131.62.217:3741
// 风格与同仓库 dev-sparkit-* Java 任务保持一致

pipeline {
    agent any

    environment {
        GIT_URL = 'https://github.com/Linn0813/SparkitTestPlatform.git'
        GIT_CRED_ID = 'github-auth'
        GIT_BRANCH = 'main'

        REMOTE_CRED = 'sparkit-tp-deploy-ssh'
        DEPLOY_HOST = '43.131.62.217'
        REMOTE_SSH = 'ubuntu@43.131.62.217'

        DEPLOY_ROOT = '/home/ubuntu/SparkitTestPlatform'
        DEPLOY_SCRIPT = "${DEPLOY_ROOT}/dev/update-cloud-server.sh"
        APP_URL = 'http://43.131.62.217:3741'
    }

    options {
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    stages {
        stage('Check out') {
            steps {
                retry(3) {
                    git branch: "${GIT_BRANCH}",
                        url: "${GIT_URL}",
                        credentialsId: "${GIT_CRED_ID}"
                }
            }
        }

        stage('Deploy to app server') {
            steps {
                withCredentials([sshUserPrivateKey(
                    credentialsId: "${REMOTE_CRED}",
                    keyFileVariable: 'SSH_KEY',
                    usernameVariable: 'SSH_USER'
                )]) {
                    sh """
                        set -euo pipefail
                        chmod 600 "\${SSH_KEY}"
                        ssh -i "\${SSH_KEY}" -o StrictHostKeyChecking=no -o IdentitiesOnly=yes \\
                            "\${SSH_USER}@${DEPLOY_HOST}" \\
                            'set -euo pipefail && chmod +x ${DEPLOY_SCRIPT} && ${DEPLOY_SCRIPT}'
                    """
                }
            }
        }
    }

    post {
        success {
            echo "✓ 部署成功 — ${APP_URL}"
        }
        failure {
            echo '✗ 部署失败 — 查看 Console Output；应用机: sudo journalctl -u sparkit-backend -n 50'
        }
    }
}
