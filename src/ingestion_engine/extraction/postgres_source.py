from sqlalchemy import create_engine, URL
from sqlalchemy.engine import Engine

from pyspark.sql import SparkSession, DataFrame

class PostgresSource:

    def __init__(self, host: str, port: int, database: str, user: str, password: str):

        url = URL.create(
            drivername="postgresql+psycopg2",
            username=user,
            password=password,
            host=host,
            port=port,
            database=database,
        )

        self.engine: Engine = create_engine(url)

    def read_table(self, spark: SparkSession, schema: str, table_name: str) -> DataFrame:

        url = self.engine.url

        jdbc_url = (
            f"jdbc:postgresql://{url.host}:{url.port}/{url.database}"
        )

        return spark.read.jdbc(
            url=jdbc_url,
            table=f"{schema}.{table_name}",
            properties={
                "user": url.username,
                "password": url.password,
                "driver": "org.postgresql.Driver",
            },
        )