from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def validate_dataframe(df: DataFrame, ingestion_config: dict) -> None:
    """
    Validates a transformed DataFrame before writing it.

    Args:
        df (DataFrame): The DataFrame to validate.
        ingestion_config (dict): The ingestion configuration dictionary containing data quality settings.

    Raises:
        ValueError: If any validation fails.
    """

    data_quality_config = ingestion_config.data_quality

    # 1. Check required columns exist
    missing_columns = [column for column in data_quality_config.core_fields if column not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # 2. Check mandatory fields for null values
    for column in data_quality_config.non_null_fields:
        null_count = (
            df
            .filter(F.col(column).isNull())
            .limit(1)
            .count()
        )

        if null_count:
            raise ValueError(f"Column '{column}' contains null values.")

    # 3. Check duplicated IDs
    duplicated_id = (
        df
        .groupBy(data_quality_config.core_fields)
        .count()
        .filter(F.col("count") > 1)
        .limit(1)
        .count()
    )

    if duplicated_id:
        raise ValueError(f"Duplicated values found in '{data_quality_config.id_column}'.")

    # 4. Check geometry validity
    invalid_geometry = (
        df
        .filter(
            ~F.expr(f"ST_IsValid(`{data_quality_config.geometry_column}`)")
        )
        .limit(1)
        .count()
    )

    if invalid_geometry:
        raise ValueError(f"Invalid geometries found in '{data_quality_config.geometry_column}'.")