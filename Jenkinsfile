// SparkitTestPlatform — Jenkins 与应用分机部署
// Jenkins: 49.51.186.145:8080  →  SSH  →  应用: 43.131.62.217:3741
//
// Jenkins 凭据 ID: sparkit-tp-deploy-ssh（ubuntu 私钥，见 dev/jenkins/README.md）

pipeline {
    agent any

    environment {
        DEPLOY_HOST = '43.131.62.217'
        DEPLOY_USER = 'ubuntu'
        DEPLOY_SCRIPT = '/home/ubuntu/SparkitTestPlatform/dev/update-cloud-server.sh'
        APP_URL = 'http://43.131.62.217:3741'
    }

    options {
        skipDefaultCheckout(true)
        timeout(time: 20, unit: 'MINUTES')
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    triggers {
        pollSCM('H/2 * * * *')
    }

    stages {
        stage('Deploy to app server') {
            steps {
                sshagent(credentials: ['sparkit-tp-deploy-ssh']) {
                    sh '''
                        set -euo pipefail
                        ssh -o StrictHostKeyChecking=accept-new \
                            "${DEPLOY_USER}@${DEPLOY_HOST}" \
                            "bash -lc 'chmod +x ${DEPLOY_SCRIPT} && ${DEPLOY_SCRIPT}'"
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "✓ 部署成功 — ${APP_URL}"
        }
        failure {
            echo '✗ 部署失败 — 查看 Console Output；应用机: journalctl -u sparkit-backend'
        }
    }
}
