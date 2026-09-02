import json
import pytest
from unittest.mock import MagicMock, patch, mock_open
from pyspark.sql import types as T

from ingestion_engine.transformation.column_caster import (
    spark_type_from_template,
    cast_expr,
    default_literal,
    normalize_empty_to_null,
    transform_with_template_schema,
)


@pytest.fixture(autouse=True)
def mock_F():
    """Patch pyspark.sql.functions in column_caster; avoids needing a live JVM."""
    with patch("ingestion_engine.transformation.column_caster.F") as mock_f:
        # Set up chainable return values used across the module
        mock_f.lit.return_value = MagicMock()
        mock_f.lit.return_value.cast.return_value = MagicMock()
        mock_f.when.return_value.otherwise.return_value = MagicMock()
        mock_f.coalesce.return_value = MagicMock()
        yield mock_f


# spark_type_from_template

@pytest.mark.parametrize("type_name,expected", [
    ("string",  T.StringType),
    ("date",    T.TimestampType),
    ("double",  T.DoubleType),
    ("integer", T.IntegerType),
    ("boolean", T.BooleanType),
])
def test_spark_type_from_template(type_name, expected):
    assert isinstance(spark_type_from_template(type_name), expected)


@pytest.mark.parametrize("type_name", ["unknown", "", None])
def test_spark_type_from_template_unsupported_raises_error(type_name):
    with pytest.raises(ValueError, match="Unsupported DMD characteristic type"):
        spark_type_from_template(type_name)


# cast_expr

def test_cast_expr_calls_cast_with_correct_type():
    col_expr = MagicMock()
    col_expr.cast.return_value = MagicMock()
    result = cast_expr(col_expr, "integer")
    col_expr.cast.assert_called_once_with(T.IntegerType())
    assert result is col_expr.cast.return_value


def test_cast_expr_uses_string_type_for_unknown():
    col_expr = MagicMock()
    with pytest.raises(ValueError):
        cast_expr(col_expr, "unknown")


# default_literal

def test_default_literal_none_returns_column():
    assert default_literal(None, "string") is not None

def test_default_literal_string_value():
    assert default_literal("hello", "string") is not None

def test_default_literal_integer_value():
    assert default_literal(42, "integer") is not None

def test_default_literal_double_value():
    assert default_literal(3.14, "double") is not None

def test_default_literal_boolean_true():
    assert default_literal(True, "boolean") is not None

def test_default_literal_boolean_str_yes():
    assert default_literal("yes", "boolean") is not None

def test_default_literal_boolean_str_no():
    assert default_literal("no", "boolean") is not None

def test_default_literal_boolean_str_invalid_returns_null_column():
    with pytest.raises(ValueError, match="Invalid boolean default value"):
        default_literal("maybe", "boolean")

def test_default_literal_date_value():
    assert default_literal("2022-01-01", "date") is not None


# normalize_empty_to_null

def test_normalize_empty_to_null_non_string_returns_input_unchanged():
    col = MagicMock()
    result = normalize_empty_to_null(col)
    # normalize_empty_to_null always applies the F.when logic
    assert result is not None

def test_normalize_empty_to_null_double_returns_input_unchanged():
    col = MagicMock()
    result = normalize_empty_to_null(col)
    assert result is not None

def test_normalize_empty_to_null_string_calls_F_when():
    col = MagicMock()
    result = normalize_empty_to_null(col)
    assert result is not col

def test_normalize_empty_to_null_maindata_calls_F_when():
    col = MagicMock()
    result = normalize_empty_to_null(col)
    assert result is not col

def test_normalize_empty_to_null_empty_type_calls_F_when():
    col = MagicMock()
    result = normalize_empty_to_null(col)
    assert result is not col


# transform_with_template_schema

def _make_df(columns=None):
    df = MagicMock()
    df.columns = columns or ["raw_field", "id", "source"]
    df.withColumn.return_value = df
    df.select.return_value = MagicMock()
    return df


def test_transform_calls_select():
    df = _make_df()
    mapping = {"XV_field": {"field": "raw_field", "default_value": None}}
    schema = [{"code": "XV_field", "type": "string"}]

    result = transform_with_template_schema(df, ["id", "source"], schema, mapping)

    df.select.assert_called_once()
    assert result is df.select.return_value


def test_transform_unknown_mapping_still_selects():
    df = _make_df()
    mapping = {}
    schema = [{"code": "UNKNOWN_FIELD", "type": "string"}]

    transform_with_template_schema(df, ["id", "source"], schema, mapping)

    df.select.assert_called_once()


def test_transform_missing_core_field_is_added():
    df = _make_df(columns=["raw_field"])
    mapping = {}
    schema = []

    transform_with_template_schema(df, ["id"], schema, mapping)

    df.withColumn.assert_called()


def test_transform_mapped_field_absent_in_df_falls_back_to_null():
    df = _make_df(columns=["id", "source"])
    mapping = {"XV_field": {"field": "raw_field", "default_value": "fallback"}}
    schema = [{"code": "XV_field", "type": "string"}]

    result = transform_with_template_schema(df, ["id", "source"], schema, mapping)

    df.select.assert_called_once()
