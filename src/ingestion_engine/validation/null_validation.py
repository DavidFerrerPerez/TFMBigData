from pyspark.sql import DataFrame
import math
from typing import Any

def remove_mandatory_nulls(df: DataFrame, ingestion_config: dict) -> DataFrame:
    """
    Removes rows from a DataFrame where any of the specified mandatory fields are null.

    Args:
        df (DataFrame): The input DataFrame.
        ingestion_config (dict): The ingestion configuration dictionary containing data quality settings.

    Returns:
        DataFrame: A new DataFrame with rows containing null values in mandatory fields removed.
    """

    mandatory_fields = ingestion_config.data_quality.non_null_fields

    for field in mandatory_fields:
        df = df.filter(df[field].isNotNull())
    return df

def is_valid(value: Any) -> bool:
    """
    Check whether a value should be considered valid.

    A value is considered invalid when it is None or NaN.

    Args:
        value: Value to validate.

    Returns:
        bool: True if the value is valid, False otherwise.
    """

    if value is None:
        return False

    try:
        return not math.isnan(value)
    except (TypeError, ValueError):
        return True