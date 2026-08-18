from ingestion_engine.extraction.postgres_source import PostgresSource
from pyspark.sql import SparkSession, DataFrame

def read_table_from_postgres(table: str, spark: SparkSession) -> DataFrame:

    postgres_source = PostgresSource()

    table_df = postgres_source.read_table(spark, schema="assets", table_name=table)

    return table_df