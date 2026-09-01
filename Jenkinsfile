pipeline {

    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    environment {
        IMAGE_NAME = "ingestion-engine"
        IMAGE_TAG = "${BUILD_NUMBER}"

        REGISTRY = "ghcr.io"
        REGISTRY_NAMESPACE = "davidferrerperez"
    }

    stages {

        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }

        stage('Build') {
            steps {
                echo "Branch: ${BRANCH_NAME}"
                echo "Building ${IMAGE_NAME}:${IMAGE_TAG}"

                sh '''
                    docker build \
                        --tag "${IMAGE_NAME}:${IMAGE_TAG}" \
                        .
                '''
            }
        }

        stage('Test') {
            steps {
                sh '''
                    TEST_CONTAINER="${IMAGE_NAME}-test-${BUILD_NUMBER}"

                    cleanup() {
                        docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true
                    }

                    trap cleanup EXIT
                    cleanup

                    mkdir -p reports

                    docker create \
                        --name "$TEST_CONTAINER" \
                        --entrypoint pdm \
                        "${IMAGE_NAME}:${IMAGE_TAG}" \
                        run pytest tests \
                        --junitxml=/tmp/test-results.xml

                    set +e
                    docker start -a "$TEST_CONTAINER"
                    TEST_EXIT_CODE=$?
                    set -e

                    docker cp \
                        "$TEST_CONTAINER:/tmp/test-results.xml" \
                        reports/test-results.xml || true

                    exit "$TEST_EXIT_CODE"
                '''
            }

            post {
                always {
                    junit(
                        allowEmptyResults: true,
                        testResults: 'reports/test-results.xml'
                    )

                    sh '''
                        docker rm -f \
                            "${IMAGE_NAME}-test-${BUILD_NUMBER}" \
                            >/dev/null 2>&1 || true
                    '''
                }
            }
        }

        stage('Publish') {
            when {
                branch 'main'
            }

            steps {
                echo "Publishing ${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:${IMAGE_TAG}"

                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-registry',
                        usernameVariable: 'REGISTRY_USER',
                        passwordVariable: 'REGISTRY_TOKEN'
                    )
                ]) {
                    sh '''
                        VERSIONED_IMAGE="${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:${IMAGE_TAG}"
                        LATEST_IMAGE="${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:latest"

                        logout_registry() {
                            docker logout "$REGISTRY" >/dev/null 2>&1 || true
                        }

                        trap logout_registry EXIT

                        echo "$REGISTRY_TOKEN" | docker login "$REGISTRY" \
                            --username "$REGISTRY_USER" \
                            --password-stdin

                        docker tag \
                            "${IMAGE_NAME}:${IMAGE_TAG}" \
                            "$VERSIONED_IMAGE"

                        docker tag \
                            "${IMAGE_NAME}:${IMAGE_TAG}" \
                            "$LATEST_IMAGE"

                        docker push "$VERSIONED_IMAGE"
                        docker push "$LATEST_IMAGE"
                    '''
                }
            }
        }
    }

    post {

        success {
            echo "Pipeline ${BUILD_NUMBER} for branch ${BRANCH_NAME} completed successfully."
        }

        failure {
            echo "Pipeline ${BUILD_NUMBER} for branch ${BRANCH_NAME} failed."
        }

        aborted {
            echo "Pipeline ${BUILD_NUMBER} for branch ${BRANCH_NAME} was aborted."
        }
    }
}