import os

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import BinaryType, StringType
from sedona.sql import st_constructors

from ingestion_engine.extraction.postgres_source import PostgresSource


def _convert_geometry_columns(df: DataFrame) -> DataFrame:
    """
    Convert PostGIS geometry columns (read as binary or hex strings via JDBC)
    into Sedona GeometryType using ST_GeomFromWKB.

    Args:
        df (DataFrame): The Spark DataFrame to convert.

    Returns:
        DataFrame: The Spark DataFrame with geometry columns converted to Sedona GeometryType.
    """
    for field in df.schema.fields:
        if isinstance(field.dataType, BinaryType):
            df = df.withColumn(field.name, st_constructors.ST_GeomFromWKB(F.col(field.name)))
        elif isinstance(field.dataType, StringType):
            sample = df.select(field.name).limit(1).collect()
            if sample and sample[0][0] and _looks_like_wkb_hex(sample[0][0]):
                df = df.withColumn(field.name, st_constructors.ST_GeomFromWKB(F.unhex(F.col(field.name))))
    return df


def _looks_like_wkb_hex(value: str) -> bool:
    """
    Heuristic: WKB hex strings start with '00' or '01' and are long even-length hex.

    Args:
        value (str): The string to check.

    Returns:
        bool: True if the string looks like a WKB hex, False otherwise.
    """
    v = value.strip()
    return len(v) >= 10 and len(v) % 2 == 0 and v[:2] in ("00", "01") and all(c in "0123456789abcdefABCDEF" for c in v)


def read_table_from_postgres(schema: str, table: str, spark: SparkSession, environment: str) -> DataFrame:

    """
    Reads a table from a PostgreSQL database using Spark JDBC.
    
    Args:
        schema (str): The schema name of the table.
        table (str): The name of the table to read.
        spark (SparkSession): The Spark session to use for reading the table.

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

    return _convert_geometry_columns(table_df)
