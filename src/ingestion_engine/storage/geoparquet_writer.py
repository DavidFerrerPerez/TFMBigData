from pathlib import Path
from tempfile import TemporaryDirectory

from pyspark.sql import DataFrame

from ingestion_engine.storage.blob_client import BlobClient


def write_df_to_geoparquet(df: DataFrame, blob_client: BlobClient, blob_path: str, overwrite: bool = True) -> None:

    """
    Write a Spark DataFrame as GeoParquet and upload it to Azure Blob Storage.

    Args:
        df: Spark DataFrame containing a geometry column.
        blob_client: Blob storage connection.
        blob_path: Destination path inside the Azure container.
        overwrite: Whether existing blobs should be overwritten.
    """

    with TemporaryDirectory(prefix="geoparquet_") as temp_dir:
        output_directory = Path(temp_dir) / "data"

        dataframe_to_write = df.coalesce(1)

        (dataframe_to_write.write
            .format("geoparquet")
            .mode("overwrite")
            .save(output_directory.as_uri()))

        parquet_files = list(output_directory.glob("part-*.parquet"))

        if len(parquet_files) != 1:
                raise RuntimeError(f"Expected exactly one GeoParquet file, but found {len(parquet_files)}")

        blob_client.upload_file(local_path=parquet_files[0], blob_path=blob_path, overwrite=overwrite)

    

    