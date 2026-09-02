from pyspark.sql import DataFrame

from ingestion_engine.storage.blob_client import BlobClient


def write_df_to_geoparquet(df: DataFrame, blob_client: BlobClient, blob_path: str, overwrite: bool = True) -> None:
    """Write a Spark DataFrame as GeoParquet directly to Azure Blob Storage."""

    spark_path = blob_client.get_spark_path(blob_path)
    mode = "overwrite" if overwrite else "errorifexists"

    (
        df.write
        .format("geoparquet")
        .mode(mode)
        .save(spark_path)
    )