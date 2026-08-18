from pyspark.sql import SparkSession

from ingestion_engine.extraction.postgres_reader import read_table_from_postgres

def extract_table(table: str, spark: SparkSession):

    df = read_table_from_postgres(table, spark)

    print(df.head())

def main():

    spark = (
            SparkSession.builder
            .appName("ingestion-engine")
            .master("local[*]")
            .getOrCreate()
        )
    
    df = extract_table("pipe", spark)

    df.show()

    spark.stop()


if __name__ == "__main__":
    main()
    