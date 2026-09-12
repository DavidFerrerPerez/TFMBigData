from unittest.mock import MagicMock, patch
from pyspark.sql.types import StructField

from ingestion_engine.extraction.postgres_reader import read_table_from_postgres

# read_table_from_postgres

ENV = {
    "POSTGRES_HOST_ENV": "myhost",
    "POSTGRES_PORT_ENV": "5432",
    "POSTGRES_DATABASE_ENV": "mydb",
    "POSTGRES_USER_ENV": "myuser",
    "POSTGRES_PASSWORD_ENV": "mypass",
}


def test_read_table_uses_env_vars():
    spark = MagicMock()
    with patch.dict("os.environ", ENV), \
         patch("ingestion_engine.extraction.postgres_reader.PostgresSource") as mock_cls, \
         patch("ingestion_engine.extraction.postgres_reader._convert_geometry_columns"):
        mock_cls.return_value = MagicMock()
        read_table_from_postgres("schema", "table", "geom", spark, "ENV")

    mock_cls.assert_called_once_with(
        host="myhost", port=5432, database="mydb", user="myuser", password="mypass"
    )


def test_read_table_calls_read_table_method():
    spark = MagicMock()
    with patch.dict("os.environ", ENV), \
         patch("ingestion_engine.extraction.postgres_reader.PostgresSource") as mock_cls, \
         patch("ingestion_engine.extraction.postgres_reader._convert_geometry_columns"):
        mock_source = MagicMock()
        mock_cls.return_value = mock_source
        read_table_from_postgres("myschema", "mytable", "geom", spark, "ENV")

    mock_source.read_table.assert_called_once_with(spark, schema="myschema", table_name="mytable")


def test_read_table_returns_converted_df():
    spark = MagicMock()
    expected = MagicMock()
    with patch.dict("os.environ", ENV), \
         patch("ingestion_engine.extraction.postgres_reader.PostgresSource") as mock_cls, \
         patch("ingestion_engine.extraction.postgres_reader._convert_geometry_columns", return_value=expected):
        mock_cls.return_value = MagicMock()
        result = read_table_from_postgres("s", "t", "geom", spark, "ENV")

    assert result is expected
