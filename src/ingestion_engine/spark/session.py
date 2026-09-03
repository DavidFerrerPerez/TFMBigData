import os

from sedona.spark import SedonaContext


def create_spark_session(
    app_name: str = "ingestion-engine",
) -> SedonaContext:
    """Create and configure a Spark session with Sedona support."""

    account_name = os.environ["AZURE_STORAGE_ACCOUNT_NAME"]
    account_key = os.environ["AZURE_STORAGE_ACCOUNT_KEY"]

    config = (
        SedonaContext.builder()
        .appName(app_name)
        .config(
            "spark.jars.packages",
            ",".join(
                [
                    "org.postgresql:postgresql:42.7.13",
                    "org.apache.sedona:sedona-spark-3.5_2.12:1.7.1",
                    "org.datasyslab:geotools-wrapper:1.7.1-28.5",
                    "org.apache.hadoop:hadoop-azure:3.3.4",
                ]
            ),
        )
        .config(
            f"spark.hadoop.fs.azure.account.key."
            f"{account_name}.blob.core.windows.net",
            account_key,
        )
        # Parquet write configuration
        .config("spark.sql.parquet.int96RebaseModeInWrite", "CORRECTED")
        # Azure Blob Storage optimization - disable rename optimization to use copy+delete
        .config("spark.hadoop.fs.azure.rename.optimization", "false")
        # Use v2 algorithm for better reliability
        .config("mapreduce.fileoutputcommitter.algorithm.version", "2")
        # Disable thread pool for Azure operations to avoid timeouts
        .config("spark.hadoop.fs.azure.thread.pool.size", "1")
        # Increase timeout for Azure operations
        .config("spark.hadoop.fs.azure.timeout", "90000")
        # Enable optimistic retry for transient failures
        .config("spark.hadoop.fs.azure.block.size", "256m")
        # Skip the final cleanup of temporary directories on failure
        # This prevents DirectoryIsNotEmpty errors
        .config("spark.hadoop.mapreduce.fileoutputcommitter.cleanup-failures.ignored", "true")
        .getOrCreate()
    )

    return SedonaContext.create(config)