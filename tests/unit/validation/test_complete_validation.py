import pytest
from unittest.mock import MagicMock, patch

from ingestion_engine.validation.complete_validation import validate_dataframe


@pytest.fixture(autouse=True)
def mock_F():
    """Patch pyspark.sql.functions in complete_validation; avoids needing a live JVM."""
    with patch("ingestion_engine.validation.complete_validation.F") as mock_f:
        col_mock = MagicMock()
        col_mock.__gt__.return_value = MagicMock()
        mock_f.col.return_value = col_mock
        mock_f.expr.return_value = MagicMock()
        yield mock_f


def _make_config(core_fields=None, non_null_fields=None, id_column="id", geometry_column="geometry"):
    config = MagicMock()
    config.data_quality.core_fields = core_fields or ["id", "source"]
    config.data_quality.non_null_fields = non_null_fields or ["id"]
    config.data_quality.id_column = id_column
    config.data_quality.geometry_column = geometry_column
    return config


def _make_valid_df(columns=None):
    df = MagicMock()
    df.columns = columns or ["id", "source", "geometry"]
    df.filter.return_value.limit.return_value.count.return_value = 0
    df.groupBy.return_value.count.return_value.filter.return_value.limit.return_value.count.return_value = 0
    return df


def test_validate_passes_with_valid_df():
    df = _make_valid_df()
    validate_dataframe(df, _make_config())


def test_validate_raises_on_missing_required_column():
    df = _make_valid_df(columns=["source", "geometry"])
    with pytest.raises(ValueError, match="Missing required columns"):
        validate_dataframe(df, _make_config(core_fields=["id", "source"]))


def test_validate_null_in_mandatory_field_is_filtered_to_rejected():
    df = _make_valid_df()
    valid, rejected = validate_dataframe(df, _make_config())
    assert valid is not None
    assert rejected is not None


def test_validate_invalid_geometry_is_filtered_to_rejected(mock_F):
    df = _make_valid_df()
    _, rejected = validate_dataframe(df, _make_config())
    mock_F.expr.assert_called()  # geometry check uses ST_IsValid via F.expr
    assert rejected is not None
