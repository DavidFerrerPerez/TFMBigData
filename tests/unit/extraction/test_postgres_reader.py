from unittest.mock import MagicMock, patch
from pyspark.sql.types import BinaryType, StringType, IntegerType, StructField

from ingestion_engine.extraction.postgres_reader import (
    _convert_geometry_columns,
    read_table_from_postgres,
)


# _convert_geometry_columns

def make_field(name, data_type):
    f = MagicMock(spec=StructField)
    f.name = name
    f.dataType = data_type
    return f


def test_convert_binary_column():
    df = MagicMock()
    df.columns = ["geom"]
    field = make_field("geom", BinaryType())
    df.schema = MagicMock()
    df.schema.__getitem__ = MagicMock(return_value=field)
    converted = MagicMock()
    df.withColumn.return_value = converted

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors"), \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df, "geom")

    df.withColumn.assert_called_once()
    assert result is converted


def test_convert_string_wkb_hex_column():
    df = MagicMock()
    df.columns = ["geom"]
    field = make_field("geom", StringType())
    df.schema = MagicMock()
    df.schema.__getitem__ = MagicMock(return_value=field)
    converted = MagicMock()
    df.withColumn.return_value = converted

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors"), \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df, "geom")

    df.withColumn.assert_called_once()
    assert result is converted


def test_execute_string_column():
    df = MagicMock()
    df.columns = ["name"]
    field = make_field("name", StringType())
    df.schema = MagicMock()
    df.schema.__getitem__ = MagicMock(return_value=field)

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors"), \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df, "name")

    df.withColumn.assert_called_once()


def test_execute_null_string_sample():
    df = MagicMock()
    df.columns = ["col"]
    field = make_field("col", StringType())
    df.schema = MagicMock()
    df.schema.__getitem__ = MagicMock(return_value=field)

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors"), \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df, "col")

    df.withColumn.assert_called_once()


def test_skip_non_geometry_types():
    df = MagicMock()
    df.columns = ["id"]
    field = make_field("id", IntegerType())
    df.schema = MagicMock()
    df.schema.__getitem__ = MagicMock(return_value=field)

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors"), \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df, "id")

    df.withColumn.assert_not_called()
    assert result is df


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
