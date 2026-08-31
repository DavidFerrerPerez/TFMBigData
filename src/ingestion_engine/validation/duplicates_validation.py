from pyspark.sql import DataFrame

def remove_duplicates(df: DataFrame, subset: list[str]) -> DataFrame:
    """
    Removes duplicate rows from a DataFrame based on a subset of columns.

    Args:
        df (DataFrame): The input DataFrame.
        subset (list[str]): A list of column names to consider for identifying duplicates.

    Returns:
        DataFrame: A new DataFrame with duplicates removed.
    """

    return df.dropDuplicates(subset)