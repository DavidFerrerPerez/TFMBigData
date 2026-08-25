import json
import os
import logging

from sedona.spark import SedonaContext

from ingestion_engine.extraction.postgres_reader import read_table_from_postgres
from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.storage.geoparquet_writer import write_df_to_geoparquet
from ingestion_engine.configuration.loader import load_ingestion_config

def run_extraction_pipeline(extraction_config, table_mapping, spark, blob_client):

    for template in extraction_config.templates:
    
        for table in table_mapping[template]:

            logging.info(f"Reading table '{table}' from schema '{extraction_config.source.db_schema}'...")

            try:
                df = read_table_from_postgres(
                    extraction_config.source.db_schema,
                    table,
                    spark
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


def main():

    logging.info("Starting the extraction pipeline...")

    extraction_config = load_ingestion_config("config/ingestion.yaml")

    config = (
        SedonaContext.builder()
        .appName("ingestion-engine")
        .config(
            "spark.jars.packages",
            ",".join([
                "org.postgresql:postgresql:42.7.13",
                "org.apache.sedona:sedona-spark-3.5_2.12:1.7.1",
                "org.datasyslab:geotools-wrapper:1.7.1-28.5",
            ])
        )
        .getOrCreate()
    )

    spark = SedonaContext.create(config)

    spark.sparkContext.setLogLevel("ERROR")
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    logging.getLogger("azure.storage").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = extraction_config.storage.container if extraction_config.storage.container else None

    if not connection_string or not container_name:
        raise ValueError("Missing Azure Blob configuration variables: AZURE_STORAGE_CONNECTION_STRING / extraction_config.storage.container")


    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    with open("config/mappings/templates_mapping.json", "r") as file:
        table_mapping = json.load(file)

    run_extraction_pipeline(extraction_config, table_mapping, spark, blob_client)

    logging.info("Extraction pipeline completed successfully.")

    spark.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
    