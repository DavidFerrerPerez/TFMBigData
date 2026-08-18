import os

from pyspark.sql import SparkSession

from ingestion_engine.extraction.postgres_reader import read_table_from_postgres
from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.storage.geoparquet_writer import write_df_to_geoparquet

def extract_table(table: str, spark: SparkSession):

    df = read_table_from_postgres(table, spark)

    return df

def main():

    spark = (
        SparkSession.builder
        .appName("ingestion-engine")
        .config(
            "spark.jars.packages",
            "org.postgresql:postgresql:42.7.13",
        )
        .getOrCreate()
    )

    blob_client = BlobClient(
        connection_string=os.environ.get("AZURE_STORAGE_CONNECTION_STRING"),
        container_name=os.environ.get("AZURE_STORAGE_CONTAINER_NAME"),
    )
    
    df = extract_table("pipe", spark)

    df.show()

    write_df_to_geoparquet(df, blob_client, "pipe.parquet")

    spark.stop()


if __name__ == "__main__":
    main()
    