def validate_blob_config(
    connection_string: str | None,
    container_name: str | None,
) -> None:
    """Validate Azure Blob Storage configuration."""

    if not connection_string:
        raise ValueError(
            "Azure Blob Storage connection string is not set."
        )

    if not container_name:
        raise ValueError(
            "Azure Blob Storage container name is not set."
        )