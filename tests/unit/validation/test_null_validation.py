from unittest.mock import MagicMock

from ingestion_engine.validation.null_validation import split_mandatory_nulls


def _make_config(non_null_fields):
    config = MagicMock()
    config.data_quality.non_null_fields = non_null_fields
    return config


# no mandatory fields

def test_no_fields_returns_original_df_as_valid():
    df = MagicMock()
    valid, _ = split_mandatory_nulls(df, _make_config([]))
    assert valid is df


def test_no_fields_returns_empty_rejected_via_filter():
    df = MagicMock()
    empty = MagicMock()
    df.filter.return_value = empty
    _, rejected = split_mandatory_nulls(df, _make_config([]))
    assert rejected is empty


def test_no_fields_filters_rejected_with_always_false_condition():
    df = MagicMock()
    split_mandatory_nulls(df, _make_config([]))
    df.filter.assert_called_once_with("1=0")


# single mandatory field

def test_single_field_valid_df_is_filtered():
    df = MagicMock()
    filtered = MagicMock()
    df.filter.return_value = filtered

    valid, _ = split_mandatory_nulls(df, _make_config(["id"]))

    assert valid is filtered


def test_single_field_rejected_df_is_not_none():
    df = MagicMock()
    df.filter.return_value = MagicMock()

    _, rejected = split_mandatory_nulls(df, _make_config(["id"]))

    assert rejected is not None


def test_single_field_filters_valid_rows_on_not_null():
    df = MagicMock()
    df.filter.return_value = MagicMock()

    split_mandatory_nulls(df, _make_config(["id"]))

    df.__getitem__.assert_called_with("id")
    df.__getitem__.return_value.isNotNull.assert_called()


def test_single_field_filters_rejected_rows_on_is_null():
    df = MagicMock()
    df.filter.return_value = MagicMock()

    split_mandatory_nulls(df, _make_config(["id"]))

    df.__getitem__.return_value.isNull.assert_called()


# two mandatory fields

def test_two_fields_chains_filters_for_valid():
    df = MagicMock()
    filtered1 = MagicMock()
    filtered2 = MagicMock()
    df.filter.return_value = filtered1
    filtered1.filter.return_value = filtered2

    valid, _ = split_mandatory_nulls(df, _make_config(["id", "name"]))

    filtered1.filter.assert_called_once()
    assert valid is filtered2


def test_two_fields_rejected_is_filtered_from_original_df():
    df = MagicMock()
    filtered1 = MagicMock()
    filtered1.filter.return_value = MagicMock()
    df.filter.return_value = filtered1

    _, rejected = split_mandatory_nulls(df, _make_config(["id", "name"]))

    # rejected comes from df.filter (called for first valid field and for the null condition)
    assert rejected is not None
