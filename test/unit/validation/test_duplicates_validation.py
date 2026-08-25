from unittest.mock import MagicMock

from ingestion_engine.validation.duplicates_validation import remove_duplicates


def test_remove_duplicates_calls_drop_duplicates_with_subset():
    df = MagicMock()
    remove_duplicates(df, ["id", "source"])
    df.dropDuplicates.assert_called_once_with(["id", "source"])


def test_remove_duplicates_returns_result_of_drop_duplicates():
    df = MagicMock()
    expected = MagicMock()
    df.dropDuplicates.return_value = expected
    assert remove_duplicates(df, ["id"]) is expected


def test_remove_duplicates_passes_empty_subset():
    df = MagicMock()
    remove_duplicates(df, [])
    df.dropDuplicates.assert_called_once_with([])
