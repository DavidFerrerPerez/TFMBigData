from unittest.mock import MagicMock

from ingestion_engine.validation.null_validation import remove_mandatory_nulls


def _make_config(non_null_fields):
    config = MagicMock()
    config.data_quality.non_null_fields = non_null_fields
    return config


def test_remove_mandatory_nulls_no_fields_returns_df_unchanged():
    df = MagicMock()
    result = remove_mandatory_nulls(df, _make_config([]))
    df.filter.assert_not_called()
    assert result is df


def test_remove_mandatory_nulls_single_field_filters_once():
    df = MagicMock()
    filtered = MagicMock()
    df.filter.return_value = filtered

    result = remove_mandatory_nulls(df, _make_config(["id"]))

    df.filter.assert_called_once()
    assert result is filtered


def test_remove_mandatory_nulls_two_fields_chains_filters():
    df = MagicMock()
    filtered1 = MagicMock()
    filtered2 = MagicMock()
    df.filter.return_value = filtered1
    filtered1.filter.return_value = filtered2

    result = remove_mandatory_nulls(df, _make_config(["id", "name"]))

    df.filter.assert_called_once()
    filtered1.filter.assert_called_once()
    assert result is filtered2


def test_remove_mandatory_nulls_filters_on_not_null():
    df = MagicMock()
    df.filter.return_value = MagicMock()

    remove_mandatory_nulls(df, _make_config(["id"]))

    df.__getitem__.assert_called_with("id")
    df.__getitem__.return_value.isNotNull.assert_called_once()
