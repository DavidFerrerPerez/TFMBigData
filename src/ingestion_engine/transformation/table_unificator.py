from pyspark.sql import DataFrame

def unify_tables(source_tables: list[DataFrame]) -> DataFrame:
    """
    Unifies multiple tables into a single table.

    Args:
        source_tables (list[DataFrame]): A list of DataFrames to unify.

    Returns:
        DataFrame: The unified DataFrame.
    """


    unified_df = source_tables[0]

    for df in source_tables[1:]:
        unified_df = unified_df.unionByName(df)

    return unified_df