import json
import os
import logging

from sedona.spark import SedonaContext

from ingestion_engine.extraction.postgres_reader import read_table_from_postgres
from ingestion_engine.logging.config import configure_logging
from ingestion_engine.spark.session import create_spark_session
from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.storage.geoparquet_writer import write_df_to_geoparquet
from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.configuration.validation import validate_blob_config

def run_extraction_pipeline(extraction_config, table_mapping, spark, blob_client, environment):

    for template in extraction_config.templates:
    
        for table in table_mapping[template]:

            logging.info(f"Reading table '{table}' from schema '{extraction_config.source.db_schema}'...")

            try:
                df = read_table_from_postgres(
                    extraction_config.source.db_schema,
                    table,
                    spark,
                    environment
                )

            except Exception as e:
                logging.error(f"Error reading table '{table}': {e}")
                continue

            logging.info(f"Writing table '{table}' to GeoParquet in Azure Blob Storage...")

            try:
                write_df_to_geoparquet(df, blob_client, f"{extraction_config.storage.paths.raw}/{table}.parquet")
            except Exception as e:
                logging.error(f"Error writing table '{table}' to GeoParquet: {e}")
                continue

            logging.info(f"Table '{table}' written to GeoParquet in Azure Blob Storage successfully.")

        logging.info(f"Source tables for template '{template}' processed successfully.")


def main(environment: str):

    logging.info("Starting the extraction pipeline...")

    extraction_config = load_ingestion_config("config/ingestion.yaml")

    spark = create_spark_session(app_name="ingestion-engine-extraction")

    configure_logging()

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = extraction_config.storage.container if extraction_config.storage.container else None

    logging.info(f"Validating blob configuration for connection string and container name... Connection String: {connection_string}, Container Name: {container_name}")

    validate_blob_config(connection_string, container_name)

    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    with open("config/mappings/templates_mapping.json", "r") as file:
        table_mapping = json.load(file)

    run_extraction_pipeline(extraction_config, table_mapping, spark, blob_client, environment)

    logging.info("Extraction pipeline completed successfully.")

    spark.stop()
    