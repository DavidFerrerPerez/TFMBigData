import os
import logging
import json

from sedona.spark import SedonaContext

from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.configuration.loader import load_ingestion_config, load_table_mapping
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


def process_template_tables(spark, blob_client: BlobClient, ingestion_config, table_mapping, dmdapi, template: str) -> list:
    """
    Process the tables for a given template.

    Args:
        spark: The Spark session.
        blob_client (BlobClient): The blob client for accessing storage.
        ingestion_config: The ingestion configuration.
        table_mapping: The table mapping for templates.
        dmdapi: The DMD API client.
        template (str): The template name.

    Returns:
        list: A list of DataFrames translated to company standard schema for the template.
    """

    source_tables = []

    template_id = dmdapi.get_template_id_by_code(template)
    template_schema = dmdapi.get_template_schema_by_id(template_id)

    for table in table_mapping[template]:

        logging.debug(f"Reading table {table} from blob storage for template {template}.")

        try:
            df = read_geoparquet_to_df(spark, blob_client, f"{ingestion_config.storage.paths.raw}/{table}.parquet")

        except Exception as e:
            logging.error(f"Error reading table {table} from blob storage: {e}")
            continue

        transformed_df = transform_with_template_schema(df, ingestion_config.data_quality.core_fields, template_schema)

        source_tables.append(transformed_df)

        logging.debug(f"Table {table} for template {template} read and transformed successfully: size is {transformed_df.count()} rows.")

    return source_tables


def run_standardization_pipeline(spark, blob_client: BlobClient, ingestion_config, table_mapping, environment = "DEV"):
    """
    Runs the standardization pipeline for the given ingestion configuration and table mapping.

    Args:
        spark: The Spark session.
        blob_client (BlobClient): The blob client for accessing storage.
        ingestion_config: The ingestion configuration.
        table_mapping: The table mapping for templates.
        environment (str, optional): The environment (default is "DEV").
    """

    dmdapi = DMDApi(dmd_api_url=os.environ[f'DMD_API_URL_{environment}'], token=os.environ[f'DMD_API_TOKEN_{environment}'])

    for template in ingestion_config.templates:

        logging.info(f"Processing template: {template}")

        # 1. Casting tables to company standard schema
        try:
            source_tables = process_template_tables(spark, blob_client, ingestion_config, table_mapping, dmdapi, template)
        except Exception as e:
            logging.error(f"Error processing template source tables for {template}: {e}")
            continue

        # 2. Unifying tables
        try:
            unified_df = unify_tables(spark, source_tables)
            logging.debug(f"Unified DataFrame for template {template}: size is {unified_df.count()} rows.")
        except Exception as e:
            logging.error(f"Error unifying tables for template {template}: {e}")
            continue

        # 3. Filling 'name' column and validating the DataFrame
        try:
            df_with_name = fill_name(unified_df)
        except Exception as e:
            logging.error(f"Error filling 'name' column for template {template}: {e}")
            continue

        try:
            df_no_duplicates = remove_duplicates(df_with_name, ingestion_config.data_quality.core_fields)

            df_no_nulls = remove_mandatory_nulls(df_no_duplicates, ingestion_config)

            df_anonymized = anonymize_dataframe(df_no_nulls, ingestion_config)

            validate_dataframe(df_anonymized, ingestion_config)

            logging.debug(f"Standardized DataFrame for template {template} validated successfully: size is {df_anonymized.count()} rows.")
        except Exception as e:
            logging.error(f"Error during validation of template {template}: {e}")
            continue

        # 4. Writing the standardized DataFrame to blob storage
        try:
            write_df_to_geoparquet(df_anonymized, blob_client, f"{ingestion_config.storage.paths.standard}/{template}.parquet")
        except Exception as e:
            logging.error(f"Error writing standardized DataFrame for template {template}: {e}")
            continue

        logging.info(f"Standardized DataFrame for template {template} written successfully to blob storage.")



def main():

    logging.info("Starting the standardization pipeline...")

    configure_logging()

    ingestion_config = load_ingestion_config("config/ingestion.yaml")
    table_mapping = load_table_mapping("config/mappings/templates_mapping.json")

    spark = create_spark_session(app_name="ingestion-engine-standardization")

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = ingestion_config.storage.container

    validate_blob_config(connection_string, container_name)

    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    run_standardization_pipeline(spark, blob_client, ingestion_config, table_mapping)

    spark.stop()

    logging.info("Standardization pipeline completed successfully.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()