import os
from sedona.spark import SedonaContext
import logging

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
                    "org.apache.hadoop:hadoop-azure:3.4.0",
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
        
        # ===== Hadoop configuration =====
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.cleanup-failures.ignored", "true")
        
        # Azure Blob Storage optimization
        .config("spark.hadoop.fs.azure.rename.optimization", "false")
        .config("spark.hadoop.fs.azure.thread.pool.size", "32")
        .config("spark.hadoop.fs.azure.timeout", "90000")
        .config("spark.hadoop.fs.azure.block.size", "268435456")
        .config("spark.hadoop.fs.azure.fast.upload", "true")
        .config("spark.hadoop.fs.azure.fast.upload.block.size", "268435456")
        
        # Suppress Azure file system warnings
        .config("spark.driver.extraJavaOptions", "-Dlog4j.logger.org.apache.hadoop.fs.azure=WARN")
        
        .getOrCreate()
    )

    # Suppress Hadoop Azure logger at Python level
    logging.getLogger("py4j.java_gateway").setLevel(logging.WARNING)
    
    return SedonaContext.create(config)