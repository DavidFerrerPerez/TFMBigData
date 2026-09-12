import os

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def pseudonymize_text_column(df: DataFrame, column_name: str, prefix: str = "ANON") -> DataFrame:
    """
    Pseudonymizes a text column using a deterministic salted hash.

    The same original value will always generate the same anonymized value
    when using the same salt.

    Null and empty values are preserved.
    """

    if column_name not in df.columns:
        return df

    original = F.col(column_name)

    hashed_value = F.substring(
        F.sha2(
            F.concat(
                F.lit(os.environ.get("PSEUDONYMIZATION_SALT", "")),
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


def pseudonymize_geometry(df: DataFrame, geometry_column: str) -> DataFrame:
    """
    Moves all geometries by the same X/Y offset.

    This preserves geometry type, shape and relative spatial relationships.
    """

    if geometry_column not in df.columns:
        return df

    return df.withColumn(
        geometry_column,
        F.expr(
            f"""
            ST_Translate(
                `{geometry_column}`,
                {os.environ.get("PSEUDONYMIZATION_OFFSET_X", 1)},
                {os.environ.get("PSEUDONYMIZATION_OFFSET_Y", 1)}
            )
            """
        ),
    )


def pseudonymize_dataframe(df: DataFrame, ingestion_config) -> DataFrame:
    """
    Pseudonymizes the specified text and geometry columns in the DataFrame.

    Args:
        df (DataFrame): The input DataFrame to be pseudonymized.
        ingestion_config: The ingestion configuration containing pseudonymization settings.

    Returns:
        DataFrame: The pseudonymized DataFrame.
    """

    for column in ingestion_config.pseudonymization.text_columns:
        df = pseudonymize_text_column(df, column)

    for column in ingestion_config.pseudonymization.geometry_columns:
        df = pseudonymize_geometry(df, column)

    return df