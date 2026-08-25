pipeline {

    agent any

    environment {
        IMAGE_NAME = "ingestion-engine-david-ferrer"
        IMAGE_TAG = "${BUILD_NUMBER}"
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
    }

    post {

        always {
            junit allowEmptyResults: true,
                  testResults: 'reports/test-results.xml'
        }

        success {
            echo 'Build and tests completed successfully.'
        }

        failure {
            echo 'Pipeline failed.'
        }
    }
}