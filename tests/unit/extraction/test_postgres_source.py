from unittest.mock import MagicMock

from ingestion_engine.extraction.postgres_source import PostgresSource


def make_source(**kwargs):
    defaults = dict(host="localhost", port=5432, database="testdb", user="usr", password="pwd")
    defaults.update(kwargs)
    return PostgresSource(**defaults)


def test_init_stores_attributes():
    source = make_source(host="myhost", port=5433, database="mydb", user="admin", password="secret")
    assert source.host == "myhost"
    assert source.port == 5433
    assert source.database == "mydb"
    assert source.user == "admin"
    assert source.password == "secret"


def test_read_table_builds_jdbc_url():
    source = make_source(host="myhost", port=5432, database="mydb")
    spark = MagicMock()
    source.read_table(spark, schema="public", table_name="roads")

    url = spark.read.jdbc.call_args.kwargs["url"]
    assert "jdbc:postgresql://myhost:5432/mydb" in url


def test_read_table_quotes_schema_and_table():
    source = make_source()
    spark = MagicMock()
    source.read_table(spark, schema="my_schema", table_name="my_table")

    table = spark.read.jdbc.call_args.kwargs["table"]
    assert table == '"my_schema"."my_table"'


def test_read_table_passes_credentials_and_driver():
    source = make_source(user="testuser", password="testpass")
    spark = MagicMock()
    source.read_table(spark, schema="s", table_name="t")

    props = spark.read.jdbc.call_args.kwargs["properties"]
    assert props["user"] == "testuser"
    assert props["password"] == "testpass"
    assert props["driver"] == "org.postgresql.Driver"


def test_read_table_returns_dataframe():
    source = make_source()
    spark = MagicMock()
    expected = MagicMock()
    spark.read.jdbc.return_value = expected

    result = source.read_table(spark, schema="s", table_name="t")
    assert result is expected
