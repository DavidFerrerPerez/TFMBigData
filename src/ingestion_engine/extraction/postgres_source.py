class PostgresSource:

    """
    A class to represent a PostgreSQL source for reading tables using Spark JDBC.
    
    """

    def __init__(self, host: str, port: int, database: str, user: str, password: str):

        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password

    def read_table(self, spark, schema: str, table_name: str):

        """
        Reads a table from the PostgreSQL database using Spark JDBC.

        Args:
            spark (SparkSession): The Spark session to use for reading the table.
            schema (str): The schema name of the table.
            table_name (str): The name of the table to read.

        Returns:
            DataFrame: A Spark DataFrame containing the table data.

        """

        jdbc_url = (
            f"jdbc:postgresql://"
            f"{self.host}:{self.port}/{self.database}"
        )
        
        return spark.read.jdbc(
            url=jdbc_url,
            table=f'"{schema}"."{table_name}"',
            properties={
                "user": self.user,
                "password": self.password,
                "driver": "org.postgresql.Driver",
            },
        )