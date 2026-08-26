pipeline {

    agent any

    environment {

        IMAGE_NAME = "ingestion-engine"

        IMAGE_TAG = "${BUILD_NUMBER}"

        REGISTRY = "ghcr.io"
        
        REGISTRY_NAMESPACE = "davidferrerperez"
    }

    stages {

        stage('Checkout') {

            steps {
                checkout scm
            }
        }

        stage('Build') {

            steps {

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
                    mkdir -p reports

                    docker run --rm \
                        -v "$WORKSPACE/reports:/reports" \
                        ${IMAGE_NAME}:${IMAGE_TAG} \
                        pdm run pytest tests \
                        --junitxml=/reports/test-results.xml
                '''
            }
        }

        stage('Publish') {

            when {
                branch 'main'
            }

            steps {

                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-registry',
                        usernameVariable: 'REGISTRY_USER',
                        passwordVariable: 'REGISTRY_TOKEN'
                    )
                ]) {

                    sh '''

                        echo "$REGISTRY_TOKEN" | \
                            docker login $REGISTRY \
                            --username "$REGISTRY_USER" \
                            --password-stdin


                        docker tag \
                            ${IMAGE_NAME}:${IMAGE_TAG} \
                            ${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:${IMAGE_TAG}


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

        stage('Deploy') {

            when {
                branch 'main'
            }

            steps {

                sh '''

                    INGESTION_IMAGE=${REGISTRY}/${REGISTRY_NAMESPACE}/${IMAGE_NAME}:${IMAGE_TAG} \
                        docker compose up -d app

                '''
            }
        }
    }

    post {

        always {

            junit(
                allowEmptyResults: true,
                testResults: 'reports/test-results.xml'
            )

        }

        success {
            echo "Pipeline ${BUILD_NUMBER} successful."
        }

        failure {
            echo "Pipeline ${BUILD_NUMBER} failed."
        }
    }
}