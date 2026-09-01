import logging
import os
import sys

from ingestion_engine.configuration.loader import load_ingestion_config, load_table_mapping
from ingestion_engine.configuration.validation import validate_blob_config
from ingestion_engine.dmd.dmd_api import DMDApi
from ingestion_engine.iotcore.iotcore_api import IOTCoreAPI
from ingestion_engine.logging.config import configure_logging
from ingestion_engine.pipelines.extract_pipeline import run_extraction_pipeline
from ingestion_engine.pipelines.standardize_pipeline import run_standardization_pipeline
from ingestion_engine.pipelines.upload_pipeline import run_upload_pipeline
from ingestion_engine.spark.session import create_spark_session
from ingestion_engine.storage.blob_client import BlobClient


def run_full_pipeline(environment: str) -> None:
    """
    Execute the full ingestion pipeline: extract → standardize → upload.

    Args:
        environment (str): Target environment (e.g. "DEV", "PRO").
    """
    configure_logging()

    environment = environment.upper()

    logging.info(f"Starting the full ingestion pipeline for environment '{environment}'...")

    ingestion_config = load_ingestion_config("config/ingestion.yaml")

    if environment not in ingestion_config.available_environments:
        raise ValueError(
            f"Invalid environment '{environment}'. "
            f"Available environments: {ingestion_config.available_environments}"
        )

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = ingestion_config.storage.container

    validate_blob_config(connection_string, container_name)

    table_mapping = load_table_mapping("config/mappings/templates_mapping.json")

    dmd_api = DMDApi(
        dmd_api_url=os.environ[f"DMD_API_URL_{environment}"],
        token=os.environ[f"DMD_API_TOKEN_{environment}"],
    )

    iotcore_api = IOTCoreAPI(
        iotcore_api_url=os.environ[f"IOTCORE_API_URL_{environment}"],
        token=os.environ[f"IOTCORE_API_TOKEN_{environment}"],
        driver=os.environ.get(f"IOTCORE_API_DRIVER_{environment}"),
    )

    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    spark = create_spark_session(app_name="ingestion-engine-full")

    try:
        logging.info("Step 1/3 — Extraction pipeline...")
        run_extraction_pipeline(ingestion_config, table_mapping, spark, blob_client)
        logging.info("Extraction pipeline completed.")

        logging.info("Step 2/3 — Standardization pipeline...")
        run_standardization_pipeline(spark, blob_client, ingestion_config, table_mapping, dmd_api)
        logging.info("Standardization pipeline completed.")

        logging.info("Step 3/3 — Upload pipeline...")
        run_upload_pipeline(spark, blob_client, ingestion_config, dmd_api, iotcore_api)
        logging.info("Upload pipeline completed.")

    finally:
        spark.stop()

    logging.info(f"Full ingestion pipeline for environment '{environment}' completed successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        raise ValueError("Must provide an environment argument.")

    run_full_pipeline(environment=sys.argv[1])
