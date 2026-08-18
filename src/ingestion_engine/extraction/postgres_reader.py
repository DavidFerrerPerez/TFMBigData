import os

from pyspark.sql import SparkSession, DataFrame

from ingestion_engine.extraction.postgres_source import PostgresSource

def read_table_from_postgres(table: str, spark: SparkSession) -> DataFrame:

    """
    Reads a table from a PostgreSQL database using Spark JDBC.
    
    Args:
        table (str): The name of the table to read.
        spark (SparkSession): The Spark session to use for reading the table.

    Returns:
        DataFrame: A Spark DataFrame containing the table data.

    """

    postgres_source = PostgresSource(
        host=os.environ.get("POSTGRES_HOST"),
        port=int(os.environ.get("POSTGRES_PORT")),
        database=os.environ.get("POSTGRES_DATABASE"),
        user=os.environ.get("POSTGRES_USER"),
        password=os.environ.get("POSTGRES_PASSWORD")
    )

    table_df = postgres_source.read_table(spark, schema="assets", table_name=table)

    return table_df