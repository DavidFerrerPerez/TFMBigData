pipeline {

    agent any

    options {
        // We perform checkout ourselves
        skipDefaultCheckout(true)

        // Avoid two builds running simultaneously
        disableConcurrentBuilds()
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
                        -t ${IMAGE_NAME}:${IMAGE_TAG} \
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

                    # Remove an old test container if one exists
                    docker rm -f "$TEST_CONTAINER" >/dev/null 2>&1 || true

                    # Create a temporary container from the built image
                    docker create \
                        --name "$TEST_CONTAINER" \
                        --entrypoint pdm \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        run pytest tests \
                        --cov=ingestion_engine \
                        --cov-report=term-missing \
                        --cov-report=xml:/tmp/coverage.xml \
                        --cov-fail-under=80 \
                        --junitxml=/tmp/test-results.xml

                    # Tests are not included in the production image,
                    # so copy them into the temporary test container
                    docker cp \
                        tests \
                        "$TEST_CONTAINER:/app/"

                    # Run tests but retain the pytest exit code
                    set +e

                    docker start -a "$TEST_CONTAINER"
                    TEST_EXIT_CODE=$?

                    set -e

                    # Copy reports into the Jenkins workspace
                    mkdir -p reports

                    docker cp \
                        "$TEST_CONTAINER:/tmp/test-results.xml" \
                        reports/test-results.xml || true

                    docker cp \
                        "$TEST_CONTAINER:/tmp/coverage.xml" \
                        reports/coverage.xml || true

                    # Make the pipeline fail if pytest failed
                    exit "$TEST_EXIT_CODE"
                '''
            }

            post {
                always {
                    junit(
                        allowEmptyResults: true,
                        testResults: 'reports/test-results.xml'
                    )
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
                        logout_registry() {
                            docker logout "$REGISTRY" >/dev/null 2>&1 || true
                        }

                        trap logout_registry EXIT

                        echo "$REGISTRY_TOKEN" | \
                            docker login "$REGISTRY" \
                            --username "$REGISTRY_USER" \
                            --password-stdin

                        # Build-number version
                        docker tag \
                            ${IMAGE_NAME}:${IMAGE_TAG} \
                            ${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:${IMAGE_TAG}

                        # Latest version
                        docker tag \
                            ${IMAGE_NAME}:${IMAGE_TAG} \
                            ${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:latest

                        docker push \
                            ${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:${IMAGE_TAG}

                        docker push \
                            ${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:latest
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
    }
}