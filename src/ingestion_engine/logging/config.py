import logging


def configure_logging() -> None:
    """Configure application logging."""

    # Azure SDK loggers
    logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)
    logging.getLogger("azure.storage").setLevel(logging.ERROR)
    logging.getLogger("azure").setLevel(logging.ERROR)
    
    # Suppress verbose HTTP/network libraries
    logging.getLogger("urllib3").setLevel(logging.ERROR)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.ERROR)
    logging.getLogger("requests").setLevel(logging.ERROR)
    
    # Suppress Hadoop/Spark Azure filesystem logs
    logging.getLogger("org.apache.hadoop.fs.azure").setLevel(logging.ERROR)
    logging.getLogger("org.apache.hadoop").setLevel(logging.ERROR)
    
    # Optional: Spark loggers (if applicable)
    logging.getLogger("pyspark").setLevel(logging.ERROR)