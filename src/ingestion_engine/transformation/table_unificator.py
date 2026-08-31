from pyspark.sql import SparkSession, DataFrame
from ingestion_engine.storage.geoparquet_reader import read_geoparquet_to_df
from ingestion_engine.storage.blob_client import BlobClient

def unify_tables(spark: SparkSession, source_tables: list[DataFrame]) -> DataFrame:
    """
    Unifies multiple tables into a single table.

    Args:
        spark (SparkSession): The Spark session.
        source_tables (list[DataFrame]): A list of DataFrames to unify.
        unified_table_name (str): The name of the unified table.

    Returns:
        DataFrame: The unified DataFrame.
    """


    unified_df = source_tables[0]

    for df in source_tables[1:]:
        unified_df = unified_df.unionByName(df)

    return unified_df