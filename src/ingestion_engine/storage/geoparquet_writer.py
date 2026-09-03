from pyspark.sql import DataFrame

from ingestion_engine.storage.blob_client import BlobClient


def write_df_to_geoparquet(df: DataFrame, blob_client: BlobClient, blob_path: str, overwrite: bool = True) -> None:

    """
    Write a Spark DataFrame as GeoParquet directly to Azure Blob Storage.

    The DataFrame is written in parallel using Spark's native Hadoop-Azure
    connector, preserving the existing partitioning instead of collapsing
    it to a single partition/file.

    Args:
        df: Spark DataFrame containing a geometry column.
        blob_client: Blob storage connection.
        blob_path: Destination path inside the Azure container.
        overwrite: Whether existing blobs should be overwritten.
    """

    spark_path = blob_client.get_spark_path(blob_path)

    (df.write
        .format("geoparquet")
        .mode("overwrite" if overwrite else "errorifexists")
        .save(spark_path))