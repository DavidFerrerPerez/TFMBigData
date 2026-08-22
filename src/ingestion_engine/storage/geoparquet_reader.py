from pyspark.sql import DataFrame, SparkSession

from ingestion_engine.storage.blob_client import BlobClient


def read_geoparquet_to_df(
    spark: SparkSession,
    blob_client: BlobClient,
    blob_path: str,
) -> DataFrame:
    """
    Read a GeoParquet dataset from Azure Blob Storage.

    Args:
        spark: Active Spark session.
        blob_client: Azure Blob Storage connection.
        blob_path: Path to the GeoParquet dataset inside the container.

    Returns:
        Spark DataFrame containing the GeoParquet data.
    """

    spark_path = blob_client.get_spark_path(blob_path)

    return (
        spark.read
        .format("geoparquet")
        .load(spark_path)
    )