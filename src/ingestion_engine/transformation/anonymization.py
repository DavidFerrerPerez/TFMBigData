import os

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def anonymize_text_column(df: DataFrame, column_name: str, prefix: str = "ANON") -> DataFrame:
    """
    Anonymizes a text column using a deterministic salted hash.

    The same original value will always generate the same anonymized value
    when using the same salt.

    Null and empty values are preserved.
    """

    original = F.col(column_name)

    hashed_value = F.substring(
        F.sha2(
            F.concat(
                F.lit(os.environ.get("ANONYMIZATION_SALT", "")),
                F.lit("|"),
                F.lower(F.trim(original)),
            ),
            256,
        ),
        1,
        16,
    )

    return df.withColumn(
        column_name,
        F.when(
            original.isNull() | (F.trim(original) == ""),
            original,
        ).otherwise(
            F.concat(
                F.lit(f"{prefix}_"),
                hashed_value,
            )
        ),
    )


def anonymize_geometry(df: DataFrame, geometry_column: str) -> DataFrame:
    """
    Moves all geometries by the same X/Y offset.

    This preserves geometry type, shape and relative spatial relationships.
    """

    return df.withColumn(
        geometry_column,
        F.expr(
            f"""
            ST_Translate(
                `{geometry_column}`,
                {os.environ.get("ANONYMIZATION_OFFSET_X", 1)},
                {os.environ.get("ANONYMIZATION_OFFSET_Y", 1)}
            )
            """
        ),
    )


def anonymize_dataframe(df: DataFrame, ingestion_config) -> DataFrame:
    """
    Anonymizes the specified text and geometry columns in the DataFrame.

    Args:
        df (DataFrame): The input DataFrame to be anonymized.
        ingestion_config: The ingestion configuration containing anonymization settings.

    Returns:
        DataFrame: The anonymized DataFrame.
    """

    for column in ingestion_config.anonymization.text_columns:
        df = anonymize_text_column(df, column)

    for column in ingestion_config.anonymization.geometry_columns:
        df = anonymize_geometry(df, column)

    return df