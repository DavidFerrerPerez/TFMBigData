from pyspark.sql import DataFrame
from pyspark.sql import functions as F

def fill_name(df: DataFrame) -> DataFrame:
    """
    If 'name' column does not exist, it is added with value = 'id'. If 'name' column exists, empty or null values are replaced with 'id' values.

    Args:
        df (DataFrame): The input DataFrame containing an 'id' column. The 'name' column will be added or updated based on the 'id' column.
    Returns:
        DataFrame: The input DataFrame with the 'name' column added or updated based on the 'id' column.
    """

    df = df.withColumn(
        "name",
        F.when(
            F.col("name").isNull() | (F.trim(F.col("name")) == ""),
            F.col("id")
        ).otherwise(F.col("name"))
    )

    return df