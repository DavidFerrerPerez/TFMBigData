import os
import logging
import json

from sedona.spark import SedonaContext

from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.transformation.table_unificator import unify_tables
from ingestion_engine.dmd.dmd_api import DMDApi
from ingestion_engine.transformation.column_caster import transform_with_template_schema
from ingestion_engine.storage.geoparquet_reader import read_geoparquet_to_df
from ingestion_engine.transformation.name_validator import fill_name
from ingestion_engine.validation.duplicates_validation import remove_duplicates
from ingestion_engine.validation.null_validation import remove_mandatory_nulls
from ingestion_engine.transformation.anonymization import anonymize_dataframe
from ingestion_engine.validation.complete_validation import validate_dataframe
from ingestion_engine.storage.geoparquet_writer import write_df_to_geoparquet
from ingestion_engine.logging.config import configure_logging
from ingestion_engine.spark.session import create_spark_session
from ingestion_engine.configuration.validation import validate_blob_config


def run_enrichment_pipeline(spark: SedonaContext, blob_client: BlobClient, ingestion_config: dict, table_mapping: dict) -> None:
    pass

def main():

    logging.info("Starting the enrichment pipeline...")

    configure_logging()

    ingestion_config = load_ingestion_config("config/ingestion.yaml")
    table_mapping = load_table_mapping("config/mappings/templates_mapping.json")

    spark = create_spark_session(app_name="ingestion-engine-enrichment")

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = ingestion_config.storage.container

    validate_blob_config(connection_string, container_name)

    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    run_enrichment_pipeline(spark, blob_client, ingestion_config, table_mapping)

    spark.stop()

    logging.info("Enrichment pipeline completed successfully.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()