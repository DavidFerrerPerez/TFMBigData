from pyspark.sql import DataFrame
from functools import reduce
import math
from typing import Any

def split_mandatory_nulls(df: DataFrame, ingestion_config: dict) -> tuple[DataFrame, DataFrame]:
    """
    Splits a DataFrame into valid and rejected rows based on mandatory null fields.

    Args:
        df (DataFrame): The input DataFrame.
        ingestion_config (dict): The ingestion configuration dictionary containing data quality settings.

    Returns:
        tuple[DataFrame, DataFrame]: A tuple of (valid_df, rejected_df) where valid_df contains
        rows where all mandatory fields are non-null, and rejected_df contains rows where at
        least one mandatory field is null.
    """

    mandatory_fields = ingestion_config.data_quality.non_null_fields

    if not mandatory_fields:
        return df, df.filter("1=0")

    valid_df = df
    for field in mandatory_fields:
        valid_df = valid_df.filter(df[field].isNotNull())

    null_condition = reduce(lambda a, b: a | b, [df[field].isNull() for field in mandatory_fields])
    rejected_df = df.filter(null_condition)

    return valid_df, rejected_df

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