import pytest
from unittest.mock import MagicMock, patch

from ingestion_engine.transformation.pseudonimization import (
    pseudonimize_text_column,
    pseudonimize_geometry,
    pseudonimize_dataframe,
)


@pytest.fixture(autouse=True)
def mock_F():
    """Patch pyspark.sql.functions in anonymization; avoids needing a live JVM."""
    with patch("ingestion_engine.transformation.anonymization.F") as mock_f:
        mock_f.when.return_value.otherwise.return_value = MagicMock()
        yield mock_f


# pseudonimize_text_column

def test_pseudonimize_text_column_calls_withColumn_with_correct_name():
    df = MagicMock()
    pseudonimize_text_column(df, "customer_name")
    df.withColumn.assert_called_once()
    assert df.withColumn.call_args[0][0] == "customer_name"


def test_pseudonimize_text_column_returns_result_of_withColumn():
    df = MagicMock()
    expected = MagicMock()
    df.withColumn.return_value = expected
    assert pseudonimize_text_column(df, "customer_name") is expected


def test_pseudonimize_text_column_preserves_column_name():
    df = MagicMock()
    pseudonimize_text_column(df, "address")
    assert df.withColumn.call_args[0][0] == "address"


# pseudonimize_geometry

def test_pseudonimize_geometry_calls_withColumn_with_geometry_column():
    df = MagicMock()
    pseudonimize_geometry(df, "geometry")
    df.withColumn.assert_called_once()
    assert df.withColumn.call_args[0][0] == "geometry"


def test_pseudonimize_geometry_returns_result_of_withColumn():
    df = MagicMock()
    expected = MagicMock()
    df.withColumn.return_value = expected
    assert pseudonimize_geometry(df, "geometry") is expected


# pseudonimize_dataframe

def test_pseudonimize_dataframe_applies_text_columns():
    config = MagicMock()
    config.anonymization.text_columns = ["customer_name", "address"]
    config.anonymization.geometry_columns = []

    df = MagicMock()
    df.withColumn.return_value = df

    pseudonimize_dataframe(df, config)
    assert df.withColumn.call_count == 2


def test_pseudonimize_dataframe_applies_geometry_columns():
    config = MagicMock()
    config.anonymization.text_columns = []
    config.anonymization.geometry_columns = ["geometry"]

    df = MagicMock()
    df.withColumn.return_value = df

    pseudonimize_dataframe(df, config)
    assert df.withColumn.call_count == 1


def test_pseudonimize_dataframe_applies_both_text_and_geometry():
    config = MagicMock()
    config.anonymization.text_columns = ["customer_name", "address"]
    config.anonymization.geometry_columns = ["geometry"]

    df = MagicMock()
    df.withColumn.return_value = df

    pseudonimize_dataframe(df, config)
    assert df.withColumn.call_count == 3


def test_pseudonimize_dataframe_empty_config_returns_df_unchanged():
    config = MagicMock()
    config.anonymization.text_columns = []
    config.anonymization.geometry_columns = []

    df = MagicMock()
    result = pseudonimize_dataframe(df, config)

    df.withColumn.assert_not_called()
    assert result is df
