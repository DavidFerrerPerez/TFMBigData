import logging


def configure_logging() -> None:
    """Configure application logging."""

    logging.getLogger(
        "azure.core.pipeline.policies.http_logging_policy"
    ).setLevel(logging.WARNING)

    logging.getLogger("azure.storage").setLevel(logging.WARNING)
    logging.getLogger("azure").setLevel(logging.WARNING)