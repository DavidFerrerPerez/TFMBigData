from pyspark.sql import DataFrame

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