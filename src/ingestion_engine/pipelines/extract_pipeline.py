import os
import logging

from datetime import datetime

from ingestion_engine.configuration.loader import load_table_mapping
from ingestion_engine.extraction.postgres_reader import read_table_from_postgres
from ingestion_engine.logging.config import configure_logging
from ingestion_engine.spark.session import create_spark_session
from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.storage.geoparquet_writer import write_df_to_geoparquet
from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.configuration.validation import validate_blob_config
from ingestion_engine.pipelines.errors import PipelineExecutionError
from ingestion_engine.storage.path_utils import run_id_to_path

def run_extraction_pipeline(extraction_config, table_mapping, spark, blob_client, environment, run_id) -> None:
    """
    Run the extraction pipeline for the given configuration.
    
    Args:
        extraction_config: The ingestion configuration.
        table_mapping: The table mapping for templates.
        spark: The Spark session.
        blob_client: The blob client for accessing storage.
        environment: The environment (e.g., "DEV").
        run_id: The unique identifier for the ingestion run.
    """
    failures = []

    for template in extraction_config.templates:
        tables = table_mapping.get(template)

        if not tables:
            message = f"No source tables configured for template '{template}'."
            logging.error(message)
            failures.append(message)
            continue

        for table in tables:
            try:
                logging.info(f"Reading table '{table}' from schema '{extraction_config.source.db_schema}'.")

                df = read_table_from_postgres(
                    extraction_config.source.db_schema,
                    table,
                    extraction_config.data_quality.geometry_column,
                    spark,
                    environment,
                )

                run_id_path = run_id_to_path(run_id)

                blob_path = f"{extraction_config.storage.paths.raw}/run_id={run_id_path}/{table}.parquet"

                logging.info(f"Writing table '{table}' to '{blob_path}'.")
                write_df_to_geoparquet(df, blob_client, blob_path)

                logging.info(f"Table '{table}' extracted successfully.")

            except Exception as e:
                logging.exception(f"Extraction failed for template '{template}', table '{table}'.")
                failures.append(f"template={template}, table={table}: {e}")

    if failures:
        raise PipelineExecutionError("extraction", failures)


def main(environment: str, run_id: str):

    logging.info(f"Starting the extraction pipeline with run ID: {run_id}...")

    extraction_config = load_ingestion_config("config/ingestion.yaml")

    spark = create_spark_session(app_name="ingestion-engine-extraction")

    configure_logging()

    if environment not in extraction_config.available_environments:
        raise ValueError(
            f"Invalid environment '{environment}'. "
            f"Available environments: {extraction_config.available_environments}"
        )

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = extraction_config.storage.container if extraction_config.storage.container else None

    logging.info(f"Validating blob configuration for connection string and container name...")

    validate_blob_config(connection_string, container_name)

    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    table_mapping = load_table_mapping("config/mappings/templates_mapping.json")

    try:
        run_extraction_pipeline(extraction_config, table_mapping, spark, blob_client, environment, run_id)
    finally:
        spark.stop()

    logging.info("Extraction pipeline completed successfully.")
    