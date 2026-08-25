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


def test_validate_raises_on_null_in_mandatory_field():
    df = _make_valid_df()
    df.filter.return_value.limit.return_value.count.return_value = 1
    with pytest.raises(ValueError, match="contains null values"):
        validate_dataframe(df, _make_config())


def test_validate_raises_on_duplicate_ids():
    df = _make_valid_df()
    df.filter.return_value.limit.return_value.count.return_value = 0  # no nulls
    df.groupBy.return_value.count.return_value.filter.return_value.limit.return_value.count.return_value = 1
    with pytest.raises(ValueError, match="Duplicated values"):
        validate_dataframe(df, _make_config())


def test_validate_raises_on_invalid_geometry():
    df = MagicMock()
    df.columns = ["id", "source", "geometry"]

    null_mock = MagicMock()
    null_mock.limit.return_value.count.return_value = 0
    geom_mock = MagicMock()
    geom_mock.limit.return_value.count.return_value = 1

    df.filter.side_effect = [null_mock, geom_mock]
    df.groupBy.return_value.count.return_value.filter.return_value.limit.return_value.count.return_value = 0

    with pytest.raises(ValueError, match="Invalid geometries"):
        validate_dataframe(df, _make_config(non_null_fields=["id"]))
