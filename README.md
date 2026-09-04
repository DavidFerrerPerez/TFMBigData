# TFMBigData

The aim of this repository is to allow the user to migrate their company data from their databases to Ídrica's DMD, cleaning and translating them to DMD standard throughout the process.

## 1. Configuration

### Requirements

- Docker Desktop with Docker Compose.
- A published ingestion image in GHCR.
- Java 17 and PDM only when running the project or tests outside Docker.

Create `config.env` locally. Do not commit this file.

```dotenv
# Source PostgreSQL database
POSTGRES_HOST_DEV=
POSTGRES_PORT_DEV=5432
POSTGRES_DATABASE_DEV=
POSTGRES_USER_DEV=
POSTGRES_PASSWORD_DEV=

# Azure Blob Storage
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_ACCOUNT_NAME=
AZURE_STORAGE_ACCOUNT_KEY=

# DMD API
DMD_API_URL_DEV=
DMD_API_TOKEN_DEV=

# IoT Core API
IOTCORE_API_URL_DEV=
IOTCORE_API_TOKEN_DEV=
IOTCORE_API_DRIVER_DEV=

# Anonymization
ANONYMIZATION_SALT=
ANONYMIZATION_OFFSET_X=
ANONYMIZATION_OFFSET_Y=

# Airflow deployment
INGESTION_IMAGE=ghcr.io/davidferrerperez/ingestion-engine:latest
INGESTION_ENVIRONMENT=DEV
DOCKER_REGISTRY_CONN_ID=github_registry
```

The suffix of environment-specific variables must match `INGESTION_ENVIRONMENT`, for example `_DEV`, `_QA`, `_PRE`, or `_PROD`.

Configure the deployment in `config/ingestion.yaml`, including the source schema, templates, Azure paths, validation fields, anonymized columns, batch size, and DMD hierarchy parent. 

Configure source tables and characteristic mappings in `config/mappings/`.

If the GHCR image is private, create an Airflow connection with:

- Connection ID: `github_registry`
- Connection type: `Docker`
- Host: `https://ghcr.io`
- Login: GitHub username
- Password: classic GitHub PAT with `read:packages`

Configure DOCKER_GID variable in `config.env`.

The PAT is stored in Airflow, not in `config.env`. If Airflow has no persistent volume, this connection must be recreated whenever its container is recreated.

## 2. Execution

Start Airflow:

```bash
docker compose --env-file config.env up -d --build airflow
```

Open [http://localhost:8081](http://localhost:8081), sign in, enable the `client_ingestion` DAG, and trigger a new run. Airflow executes:

```text
validate_configuration -> extract -> standardize -> upload
```

Each stage uses the same Airflow run ID and runs in a temporary container created from `INGESTION_IMAGE`. View progress and errors from the task logs in the Airflow interface.

When changing `INGESTION_IMAGE` or another value in `config.env`, recreate Airflow so it loads the new configuration:

```bash
docker compose --env-file config.env up -d --force-recreate airflow
```

Stop Airflow without deleting its persistent data:

```bash
docker compose down
```

Do not use `docker compose down -v` unless you also want to delete Airflow connections and execution history.

## 3. Tests

Install the project and test dependencies with PDM, then execute the tests:

```bash
pdm install -G test
pdm run pytest tests
```


To generate a coverage report:

```bash
pdm run pytest tests --cov=ingestion_engine --cov-report=term-missing
```

Jenkins also runs `pytest` during each configured branch build. A successful `main` build publishes both a numbered image tag and `latest` to GHCR.
