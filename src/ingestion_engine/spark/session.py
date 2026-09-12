import os
from sedona.spark import SedonaContext
import logging


def create_spark_session(
    app_name: str = "ingestion-engine",
) -> SedonaContext:
    """Create and configure a Spark session with Sedona support."""

    account_name = os.environ["AZURE_STORAGE_ACCOUNT_NAME"]
    account_key = os.environ["AZURE_STORAGE_ACCOUNT_KEY"]

    spark = (
        SedonaContext.builder()
        .appName(app_name)
        .config(
            "spark.jars.packages",
            ",".join(
                [
                    "org.postgresql:postgresql:42.7.13",
                    "org.apache.sedona:sedona-spark-3.5_2.12:1.7.2",
                    "org.apache.hadoop:hadoop-azure:3.4.0",
                ]
            ),
        )
        .config(
            f"spark.hadoop.fs.azure.account.key."
            f"{account_name}.blob.core.windows.net",
            account_key,
        )
        .config("spark.sql.parquet.int96RebaseModeInWrite", "CORRECTED")
        .config("spark.ui.showConsoleProgress", "false")
        
        .config("spark.hadoop.mapreduce.fileoutputcommitter.algorithm.version", "2")
        .config("spark.hadoop.mapreduce.fileoutputcommitter.cleanup-failures.ignored", "true")
        
        .config("spark.hadoop.fs.azure.rename.optimization", "false")
        .config("spark.hadoop.fs.azure.thread.pool.size", "32")
        .config("spark.hadoop.fs.azure.timeout", "90000")
        .config("spark.hadoop.fs.azure.block.size", "268435456")
        .config("spark.hadoop.fs.azure.fast.upload", "true")
        .config("spark.hadoop.fs.azure.fast.upload.block.size", "268435456")
        
        .config("spark.driver.extraJavaOptions", "-Dlog4j.logger.org.apache.hadoop.fs.azure=WARN")
        
        .getOrCreate()
    )

    logging.getLogger("py4j.java_gateway").setLevel(logging.WARNING)

    # Suppress noisy JVM-side cleanup logs produced by Hadoop committers on WASB.
    try:
        jvm = spark.sparkContext._jvm
        noisy_loggers = [
            "org.apache.hadoop.mapreduce.lib.output.FileOutputCommitter",
            "org.apache.hadoop.fs.azure",
            "org.apache.hadoop.fs.azure.AzureNativeFileSystemStore",
            "org.apache.hadoop.fs.azure.AzureFileSystemThreadPoolExecutor",
            "org.apache.spark.sql.execution.datasources.parquet.GeoParquetFileFormat",
        ]

        # Spark images can use either Log4j 1.x bridge or Log4j2.
        # Try both APIs to keep behavior consistent across environments.
        try:
            log_manager = jvm.org.apache.log4j.LogManager
            level = jvm.org.apache.log4j.Level
            for logger_name in noisy_loggers:
                log_manager.getLogger(logger_name).setLevel(level.FATAL)
        except Exception:
            pass

        try:
            configurator = jvm.org.apache.logging.log4j.core.config.Configurator
            level = jvm.org.apache.logging.log4j.Level
            for logger_name in noisy_loggers:
                configurator.setLevel(logger_name, level.FATAL)
        except Exception:
            pass
    except Exception:
        # Keep session creation resilient if logger classes differ across Spark images.
        pass

    return SedonaContext.create(spark)