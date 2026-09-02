import os

import pendulum
from airflow.exceptions import AirflowException
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.sdk import DAG, task


ENVIRONMENT = os.getenv("INGESTION_ENVIRONMENT", "DEV").upper()
IMAGE = os.getenv("INGESTION_IMAGE", "")
DOCKER_REGISTRY_CONN_ID = os.getenv("DOCKER_REGISTRY_CONN_ID") or None

REQUIRED_VARIABLES = [
    "INGESTION_IMAGE",
    f"POSTGRES_HOST_{ENVIRONMENT}",
    f"POSTGRES_PORT_{ENVIRONMENT}",
    f"POSTGRES_DATABASE_{ENVIRONMENT}",
    f"POSTGRES_USER_{ENVIRONMENT}",
    f"POSTGRES_PASSWORD_{ENVIRONMENT}",
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_STORAGE_ACCOUNT_NAME",
    "AZURE_STORAGE_ACCOUNT_KEY",
    f"DMD_API_URL_{ENVIRONMENT}",
    f"DMD_API_TOKEN_{ENVIRONMENT}",
    f"IOTCORE_API_URL_{ENVIRONMENT}",
    f"IOTCORE_API_TOKEN_{ENVIRONMENT}",
    f"IOTCORE_API_DRIVER_{ENVIRONMENT}",
    "ANONYMIZATION_SALT",
    "ANONYMIZATION_OFFSET_X",
    "ANONYMIZATION_OFFSET_Y",
]

PRIVATE_ENVIRONMENT = {
    variable: os.getenv(variable, "")
    for variable in REQUIRED_VARIABLES
    if variable != "INGESTION_IMAGE"
}


@task
def validate_configuration() -> None:
    missing = [variable for variable in REQUIRED_VARIABLES if not os.getenv(variable)]
    if missing:
        raise AirflowException(f"Missing required environment variables: {', '.join(missing)}")


def create_pipeline_task(stage: str) -> DockerOperator:
    return DockerOperator(
        task_id=stage,
        image=IMAGE or "ingestion-image-not-configured",
        command=f'run --stage {stage} --environment {ENVIRONMENT} --run-id "{{{{ run_id }}}}"',
        docker_url="unix://var/run/docker.sock",
        docker_conn_id=DOCKER_REGISTRY_CONN_ID,
        network_mode="ingestion-network",
        private_environment=PRIVATE_ENVIRONMENT,
        force_pull=True,
        auto_remove="success",
        mount_tmp_dir=False,
    )


with DAG(
    dag_id="client_ingestion",
    start_date=pendulum.datetime(2026, 9, 1, tz="Europe/Madrid"),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["ingestion"],
) as dag:
    validate = validate_configuration()
    extract = create_pipeline_task("extract")
    standardize = create_pipeline_task("standardize")
    upload = create_pipeline_task("upload")

    validate >> extract >> standardize >> upload