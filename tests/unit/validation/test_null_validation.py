import math

from ingestion_engine.validation.null_validation import is_valid


def test_is_valid_returns_false_for_none():
    assert is_valid(None) is False


def test_is_valid_returns_false_for_nan():
    assert is_valid(math.nan) is False


def test_is_valid_returns_true_for_regular_values():
    assert is_valid("value") is True
    assert is_valid(42) is True
