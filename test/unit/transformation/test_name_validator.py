import pytest
from unittest.mock import MagicMock, patch

from ingestion_engine.transformation.name_validator import fill_name


@pytest.fixture(autouse=True)
def mock_F():
    """Patch pyspark.sql.functions in name_validator; avoids needing a live JVM."""
    with patch("ingestion_engine.transformation.name_validator.F") as mock_f:
        mock_f.when.return_value.otherwise.return_value = MagicMock()
        yield mock_f


def test_fill_name_calls_withColumn_with_name_key():
    df = MagicMock()
    fill_name(df)
    df.withColumn.assert_called_once()
    assert df.withColumn.call_args[0][0] == "name"


def test_fill_name_returns_result_of_withColumn():
    df = MagicMock()
    expected = MagicMock()
    df.withColumn.return_value = expected
    assert fill_name(df) is expected
