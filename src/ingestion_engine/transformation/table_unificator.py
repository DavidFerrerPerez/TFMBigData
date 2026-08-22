from pyspark.sql import SparkSession, DataFrame
from ingestion_engine.storage.geoparquet_reader import read_geoparquet_to_df
from ingestion_engine.storage.blob_client import BlobClient

def unify_tables(spark: SparkSession, blob_client: BlobClient, source_tables: list[str], unified_table_name: str) -> DataFrame:
    """
    Unifies multiple tables into a single table.

    Args:
        spark (SparkSession): The Spark session.
        source_tables (list[str]): A list of table names to unify.
        unified_table_name (str): The name of the unified table.

    Returns:
        DataFrame: The unified DataFrame.
    """


    unified_df = read_geoparquet_to_df(spark, blob_client, source_tables[0])

    for table_name in source_tables[1:]:
        df = read_geoparquet_to_df(spark, blob_client, table_name)
        unified_df = unified_df.unionByName(df)

    return unified_df