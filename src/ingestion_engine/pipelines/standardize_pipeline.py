import os
import logging
import json

from sedona.spark import SedonaContext

from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.transformation.table_unificator import unify_tables


def run_standardization_pipeline(spark, blob_client: BlobClient, ingestion_config, table_mapping):

    df = unify_tables(spark, blob_client, ingestion_config, table_mapping)

def main():

    logging.info("Starting the standardization pipeline...")
    
    ingestion_config = load_ingestion_config("config/ingestion.yaml")

    config = (
        SedonaContext.builder()
        .appName("ingestion-engine")
        .config(
            "spark.jars.packages",
            ",".join([
                "org.postgresql:postgresql:42.7.13",
                "org.apache.sedona:sedona-spark-3.5_2.12:1.7.1",
                "org.datasyslab:geotools-wrapper:1.7.1-28.5",
                "org.apache.hadoop:hadoop-azure:3.3.4",
            ])
        )
        .config(
            f"spark.hadoop.fs.azure.account.key.{os.environ['AZURE_STORAGE_ACCOUNT_NAME']}.blob.core.windows.net",
            os.environ["AZURE_STORAGE_ACCOUNT_KEY"],
        )
        .getOrCreate()
    )

    spark = SedonaContext.create(config)

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = ingestion_config.storage.container if ingestion_config.storage.container else None

    if not connection_string or not container_name:
        raise ValueError("Missing Azure Blob configuration variables: AZURE_STORAGE_CONNECTION_STRING / ingestion_config.storage.container")


    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    with open("config/mappings/templates_mapping.json", "r") as file:
            table_mapping = json.load(file)

    run_standardization_pipeline(spark, blob_client, ingestion_config, table_mapping)

    spark.stop()

    logging.info("Standardization pipeline completed successfully.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()