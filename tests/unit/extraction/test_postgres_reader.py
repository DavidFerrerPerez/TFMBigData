from unittest.mock import MagicMock, patch
from pyspark.sql.types import BinaryType, StringType, IntegerType, StructField

from ingestion_engine.extraction.postgres_reader import (
    _looks_like_wkb_hex,
    _convert_geometry_columns,
    read_table_from_postgres,
)


# _looks_like_wkb_hex

def test_wkb_hex_valid_little_endian():
    assert _looks_like_wkb_hex("0101000000" + "a" * 10) is True

def test_wkb_hex_valid_big_endian():
    assert _looks_like_wkb_hex("0000000001" + "b" * 10) is True

def test_wkb_hex_too_short():
    assert _looks_like_wkb_hex("01234567") is False

def test_wkb_hex_odd_length():
    assert _looks_like_wkb_hex("010000000") is False

def test_wkb_hex_wrong_prefix():
    assert _looks_like_wkb_hex("0200000000" + "0" * 10) is False

def test_wkb_hex_non_hex_chars():
    assert _looks_like_wkb_hex("01ZZZZZZZZ" + "0" * 10) is False

def test_wkb_hex_plain_text():
    assert _looks_like_wkb_hex("hello world") is False

def test_wkb_hex_strips_whitespace():
    assert _looks_like_wkb_hex("  0101000000" + "0" * 10 + "  ") is True


# _convert_geometry_columns

def make_field(name, data_type):
    f = MagicMock(spec=StructField)
    f.name = name
    f.dataType = data_type
    return f


def test_convert_binary_column():
    df = MagicMock()
    df.schema.fields = [make_field("geom", BinaryType())]
    converted = MagicMock()
    df.withColumn.return_value = converted

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors") as mock_st, \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df)

    df.withColumn.assert_called_once_with("geom", mock_st.ST_GeomFromWKB.return_value)
    assert result is converted


def test_convert_string_wkb_hex_column():
    df = MagicMock()
    df.schema.fields = [make_field("geom", StringType())]
    df.select.return_value.limit.return_value.collect.return_value = [["0101000000" + "0" * 30]]
    converted = MagicMock()
    df.withColumn.return_value = converted

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors") as mock_st, \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df)

    df.withColumn.assert_called_once()
    assert result is converted


def test_skip_plain_string_column():
    df = MagicMock()
    df.schema.fields = [make_field("name", StringType())]
    df.select.return_value.limit.return_value.collect.return_value = [["some text"]]

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors"), \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df)

    df.withColumn.assert_not_called()
    assert result is df


def test_skip_null_string_sample():
    df = MagicMock()
    df.schema.fields = [make_field("col", StringType())]
    df.select.return_value.limit.return_value.collect.return_value = [[None]]

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors"), \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df)

    df.withColumn.assert_not_called()


def test_skip_non_geometry_types():
    df = MagicMock()
    df.schema.fields = [make_field("id", IntegerType())]

    with patch("ingestion_engine.extraction.postgres_reader.st_constructors"), \
         patch("ingestion_engine.extraction.postgres_reader.F"):
        result = _convert_geometry_columns(df)

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
        read_table_from_postgres("schema", "table", spark, "ENV")

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
        read_table_from_postgres("myschema", "mytable", spark, "ENV")

    mock_source.read_table.assert_called_once_with(spark, schema="myschema", table_name="mytable")


def test_read_table_returns_converted_df():
    spark = MagicMock()
    expected = MagicMock()
    with patch.dict("os.environ", ENV), \
         patch("ingestion_engine.extraction.postgres_reader.PostgresSource") as mock_cls, \
         patch("ingestion_engine.extraction.postgres_reader._convert_geometry_columns", return_value=expected):
        mock_cls.return_value = MagicMock()
        result = read_table_from_postgres("s", "t", spark, "ENV")

    assert result is expected
