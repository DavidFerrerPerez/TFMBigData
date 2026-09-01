import os

import pendulum
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import DAG


IMAGE = "ingestion-engine-david-ferrer:latest"
ENVIRONMENT = "DEV"

COMMON_ENVIRONMENT = {
    # PostgreSQL
    f"POSTGRES_HOST_{ENVIRONMENT}": os.environ[f"POSTGRES_HOST_{ENVIRONMENT}"],
    f"POSTGRES_PORT_{ENVIRONMENT}": os.environ[f"POSTGRES_PORT_{ENVIRONMENT}"],
    f"POSTGRES_DATABASE_{ENVIRONMENT}": os.environ[f"POSTGRES_DATABASE_{ENVIRONMENT}"],
    f"POSTGRES_USER_{ENVIRONMENT}": os.environ[f"POSTGRES_USER_{ENVIRONMENT}"],
    f"POSTGRES_PASSWORD_{ENVIRONMENT}": os.environ[f"POSTGRES_PASSWORD_{ENVIRONMENT}"],

    # Azure Blob Storage
    "AZURE_STORAGE_CONNECTION_STRING": os.environ["AZURE_STORAGE_CONNECTION_STRING"],
    "AZURE_STORAGE_ACCOUNT_NAME": os.environ["AZURE_STORAGE_ACCOUNT_NAME"],
    "AZURE_STORAGE_ACCOUNT_KEY": os.environ["AZURE_STORAGE_ACCOUNT_KEY"],

    # DMD
    f"DMD_API_URL_{ENVIRONMENT}": os.environ[f"DMD_API_URL_{ENVIRONMENT}"],
    f"DMD_API_TOKEN_{ENVIRONMENT}": os.environ[f"DMD_API_TOKEN_{ENVIRONMENT}"],

    # IoT Core
    f"IOTCORE_API_URL_{ENVIRONMENT}": os.environ[f"IOTCORE_API_URL_{ENVIRONMENT}"],
    f"IOTCORE_API_TOKEN_{ENVIRONMENT}": os.environ[f"IOTCORE_API_TOKEN_{ENVIRONMENT}"],
    f"IOTCORE_API_DRIVER_{ENVIRONMENT}": os.environ[f"IOTCORE_API_DRIVER_{ENVIRONMENT}"],

    # Anonymization
    "ANONYMIZATION_SALT": os.environ["ANONYMIZATION_SALT"],
    "ANONYMIZATION_OFFSET_X": os.environ["ANONYMIZATION_OFFSET_X"],
    "ANONYMIZATION_OFFSET_Y": os.environ["ANONYMIZATION_OFFSET_Y"],
}


with DAG(
    dag_id="client_ingestion",
    start_date=pendulum.datetime(2026, 9, 1, tz="Europe/Madrid"),
    schedule=None,
    catchup=False,
) as dag:

    extract = DockerOperator(
        task_id="extract",
        image=IMAGE,
        command=f"run --stage extract --environment {ENVIRONMENT}",
        docker_url="unix://var/run/docker.sock",
        network_mode="ingestion-network",
        environment=COMMON_ENVIRONMENT,
        auto_remove="success",
        mount_tmp_dir=False,
    )

    standardize = DockerOperator(
        task_id="standardize",
        image=IMAGE,
        command=f"run --stage standardize --environment {ENVIRONMENT}",
        docker_url="unix://var/run/docker.sock",
        network_mode="ingestion-network",
        environment=COMMON_ENVIRONMENT,
        auto_remove="success",
        mount_tmp_dir=False,
    )

    upload = DockerOperator(
        task_id="upload",
        image=IMAGE,
        command=f"run --stage upload --environment {ENVIRONMENT}",
        docker_url="unix://var/run/docker.sock",
        network_mode="ingestion-network",
        environment=COMMON_ENVIRONMENT,
        auto_remove="success",
        mount_tmp_dir=False,
    )

    extract >> standardize >> upload