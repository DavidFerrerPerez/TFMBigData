import os

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
import pyspark.sql.types as T


from ingestion_engine.extraction.postgres_source import PostgresSource


def _convert_geometry_columns(df: DataFrame, geometry_column: str) -> DataFrame:
    if geometry_column not in df.columns:
        return df
    column = geometry_column

    field = df.schema[column]

    if isinstance(field.dataType, T.BinaryType):
        df = df.withColumn(column, F.expr(f"ST_GeomFromWKB(`{column}`)"))

    elif isinstance(field.dataType, T.StringType):
        df = df.withColumn(column, F.expr(f"ST_GeomFromWKB(unhex(`{column}`))"))

    return df


def read_table_from_postgres(schema: str, table: str, geometry_column: str, spark: SparkSession, environment: str) -> DataFrame:

    """
    Reads a table from a PostgreSQL database using Spark JDBC.
    
    Args:
        schema (str): The schema name of the table.
        table (str): The name of the table to read.
        geometry_column (str): The name of the geometry column to convert.
        spark (SparkSession): The Spark session to use for reading the table.
        environment (str): The environment (e.g., "DEV") to use for fetching PostgreSQL connection details.

    Returns:
        DataFrame: A Spark DataFrame containing the table data, with geometry
                   columns converted to Sedona GeometryType.

    """

    postgres_source = PostgresSource(
        host=os.environ.get(f"POSTGRES_HOST_{environment}"),
        port=int(os.environ.get(f"POSTGRES_PORT_{environment}")),
        database=os.environ.get(f"POSTGRES_DATABASE_{environment}"),
        user=os.environ.get(f"POSTGRES_USER_{environment}"),
        password=os.environ.get(f"POSTGRES_PASSWORD_{environment}")
    )

    table_df = postgres_source.read_table(spark, schema=schema, table_name=table)

    return _convert_geometry_columns(table_df, geometry_column)
