from unittest.mock import MagicMock
from datetime import date
import pytest

from ingestion_engine.dmd.characteristics import (
    create_characteristics_list,
    _normalize_characteristic_name,
    set_default_value,
    build_characteristics,
    get_characteristic_value,
    _handle_double,
    _handle_integer,
    _handle_date,
    get_maindata_value_id,
    add_iot_signals,
)


# create_characteristics_list tests

def test_create_characteristics_list_basic():
    """Test that create_characteristics_list creates base characteristics."""
    template_chars = [
        {"name": "Name", "code": "name_code", "type": "string"},
        {"name": "Type", "code": "type_code", "type": "string"},
        {"name": "Status", "code": "status_code", "type": "maindata"},
    ]
    
    result = create_characteristics_list(template_chars)
    
    assert len(result) == 3
    assert result[0]["code"] == "name_code"
    assert result[1]["code"] == "type_code"
    assert result[2]["code"] == "status_code"


def test_create_characteristics_list_skips_iotsynoptic():
    """Test that create_characteristics_list skips iotsynoptic types."""
    template_chars = [
        {"name": "Name", "code": "name_code", "type": "string"},
        {"name": "Synoptic", "code": "synoptic_code", "type": "iotsynoptic"},
        {"name": "Type", "code": "type_code", "type": "string"},
    ]
    
    result = create_characteristics_list(template_chars)
    
    # Should only have 2 items (skipping iotsynoptic)
    assert len(result) == 2
    assert result[0]["code"] == "name_code"
    assert result[1]["code"] == "type_code"


def test_create_characteristics_list_skips_iotsinoptic():
    """Test that create_characteristics_list skips iotsinoptic types (typo variant)."""
    template_chars = [
        {"name": "Name", "code": "name_code", "type": "string"},
        {"name": "Synoptic", "code": "synoptic_code", "type": "iotsinoptic"},
    ]
    
    result = create_characteristics_list(template_chars)
    
    assert len(result) == 1
    assert result[0]["code"] == "name_code"


# _normalize_characteristic_name tests

def test_normalize_characteristic_name_replaces_spaces():
    """Test that spaces are replaced with underscores."""
    result = _normalize_characteristic_name("Asset Name")
    assert result == "Asset_Name"


def test_normalize_characteristic_name_handles_dash_pattern():
    """Test that '_-_' pattern is replaced with single underscore."""
    result = _normalize_characteristic_name("Status_-_Value")
    assert result == "Status_Value"


def test_normalize_characteristic_name_handles_none():
    """Test that None input returns empty string."""
    result = _normalize_characteristic_name(None)
    assert result == ""


def test_normalize_characteristic_name_handles_complex_case():
    """Test complex normalization."""
    result = _normalize_characteristic_name("Asset Name_-_Status")
    assert result == "Asset_Name_Status"


# set_default_value tests

def test_set_default_value_double_returns_zero_float():
    """Test that double type returns 0.0."""
    result = set_default_value("double")
    assert result == 0.0
    assert isinstance(result, float)


def test_set_default_value_integer_returns_zero_int():
    """Test that integer type returns 0."""
    result = set_default_value("integer")
    assert result == 0
    assert isinstance(result, int)


def test_set_default_value_maindata_returns_none():
    """Test that maindata type returns None."""
    result = set_default_value("maindata")
    assert result is None


def test_set_default_value_date_returns_none():
    """Test that date type returns None."""
    result = set_default_value("date")
    assert result is None


def test_set_default_value_string_returns_empty_string():
    """Test that string and unknown types return empty string."""
    assert set_default_value("string") == ""
    assert set_default_value("unknown") == ""
    assert set_default_value(None) == ""


# _handle_double tests

def test_handle_double_converts_to_string():
    """Test that _handle_double converts numbers to string."""
    assert _handle_double(3.14) == "3.14"
    assert _handle_double(10) == "10"


def test_handle_double_returns_zero_for_none():
    """Test that _handle_double returns '0.0' for None."""
    assert _handle_double(None) == "0.0"


def test_handle_double_converts_strings_to_string():
    """Test that _handle_double converts valid values to string."""
    assert _handle_double(3.14) == "3.14"
    assert _handle_double(10) == "10"
    assert _handle_double("3.14") == "3.14"


# _handle_integer tests

def test_handle_integer_converts_to_string():
    """Test that _handle_integer converts numbers to string."""
    assert _handle_integer(42) == "42"
    assert _handle_integer(3.7) == "3"  # Truncates decimal


def test_handle_integer_returns_zero_for_none():
    """Test that _handle_integer returns '0' for None."""
    assert _handle_integer(None) == "0"


def test_handle_integer_converts_to_string():
    """Test that _handle_integer converts numbers to string."""
    assert _handle_integer(42) == "42"
    assert _handle_integer(3.7) == "3"  # Truncates decimal
    assert _handle_integer("10") == "10"


# _handle_date tests

def test_handle_date_converts_to_isoformat():
    """Test that _handle_date converts date to ISO format."""
    test_date = date(2023, 12, 25)
    result = _handle_date(test_date)
    assert result == "2023-12-25"


def test_handle_date_returns_none_for_none():
    """Test that _handle_date returns None for None value."""
    assert _handle_date(None) is None


def test_handle_date_converts_to_isoformat():
    """Test that _handle_date converts date to ISO format."""
    test_date = date(2023, 12, 25)
    result = _handle_date(test_date)
    assert result == "2023-12-25"


# get_characteristic_value tests

def test_get_characteristic_value_double():
    """Test that double values are handled correctly."""
    dmd_api = MagicMock()
    result = get_characteristic_value("double", 3.14, "code", dmd_api)
    assert result == "3.14"


def test_get_characteristic_value_integer():
    """Test that integer values are handled correctly."""
    dmd_api = MagicMock()
    result = get_characteristic_value("integer", 42, "code", dmd_api)
    assert result == "42"


def test_get_characteristic_value_date():
    """Test that date values are handled correctly."""
    dmd_api = MagicMock()
    test_date = date(2023, 12, 25)
    result = get_characteristic_value("date", test_date, "code", dmd_api)
    assert result == "2023-12-25"


def test_get_characteristic_value_maindata():
    """Test that maindata values are looked up via DMD API."""
    dmd_api = MagicMock()
    dmd_api.get_maindata_values_by_code.return_value = {"Active": 1, "Inactive": 2}
    
    result = get_characteristic_value("maindata", "Active", "status_code", dmd_api)
    
    assert result == 1
    dmd_api.get_maindata_values_by_code.assert_called_once_with("status_code")


def test_get_characteristic_value_string_passthrough():
    """Test that string values are returned as-is."""
    dmd_api = MagicMock()
    result = get_characteristic_value("string", "Hello", "code", dmd_api)
    assert result == "Hello"


# get_maindata_value_id tests

def test_get_maindata_value_id_returns_id():
    """Test that get_maindata_value_id returns the correct ID."""
    dmd_api = MagicMock()
    dmd_api.get_maindata_values_by_code.return_value = {"Active": 1, "Inactive": 2}
    
    result = get_maindata_value_id("Active", "status_code", dmd_api)
    
    assert result == 1


def test_get_maindata_value_id_returns_none_for_none():
    """Test that get_maindata_value_id returns None for None value."""
    dmd_api = MagicMock()
    
    result = get_maindata_value_id(None, "status_code", dmd_api)
    
    assert result is None


def test_get_maindata_value_id_returns_none_for_unknown():
    """Test that get_maindata_value_id returns None for 'Unknown' value."""
    dmd_api = MagicMock()
    
    result = get_maindata_value_id("Unknown", "status_code", dmd_api)
    
    assert result is None


def test_get_maindata_value_id_returns_none_for_missing_value():
    """Test that get_maindata_value_id returns None when value not in maindata."""
    dmd_api = MagicMock()
    dmd_api.get_maindata_values_by_code.return_value = {"Active": 1}
    
    result = get_maindata_value_id("Inactive", "status_code", dmd_api)
    
    assert result is None


# add_iot_signals tests

def test_add_iot_signals_returns_signal_list():
    """Test that add_iot_signals returns list of signal definitions."""
    iotcore_api = MagicMock()
    iotcore_api.get_uids_from_tag_name.return_value = ["uid1", "uid2"]
    
    result = add_iot_signals("asset-001", iotcore_api)
    
    assert len(result) == 2
    assert result[0] == {"uid": "uid1", "type": "SIGNAL", "name": "asset-001"}
    assert result[1] == {"uid": "uid2", "type": "SIGNAL", "name": "asset-001"}


def test_add_iot_signals_filters_empty_uids():
    """Test that add_iot_signals filters out empty UIDs."""
    iotcore_api = MagicMock()
    iotcore_api.get_uids_from_tag_name.return_value = ["uid1", "", "uid2", None]
    
    result = add_iot_signals("asset-001", iotcore_api)
    
    # Should only have uid1 and uid2 (empty and None are filtered)
    assert len(result) == 2
    assert result[0]["uid"] == "uid1"
    assert result[1]["uid"] == "uid2"


def test_add_iot_signals_returns_empty_list_for_no_uids():
    """Test that add_iot_signals returns empty list when no UIDs found."""
    iotcore_api = MagicMock()
    iotcore_api.get_uids_from_tag_name.return_value = []
    
    result = add_iot_signals("asset-001", iotcore_api)
    
    assert result == []


# build_characteristics tests

def test_build_characteristics_with_string_type():
    """Test that build_characteristics handles string characteristics."""
    config = MagicMock()
    config.data_quality.id_column = "id"
    
    dmd_api = MagicMock()
    iotcore_api = MagicMock()
    
    template_chars = [
        {"name": "name", "code": "asset_name", "type": "string"},
    ]
    
    row = MagicMock()
    row.asDict.return_value = {"id": "001", "asset_name": "Pump A"}
    
    result = build_characteristics(template_chars, row, dmd_api, iotcore_api, config)
    
    assert len(result) == 1
    assert result[0]["name"] == "name"
    assert result[0]["value"] == "Pump A"
    assert result[0]["code"] == "asset_name"


def test_build_characteristics_uses_default_when_field_missing():
    """Test that build_characteristics uses default value when field is missing."""
    config = MagicMock()
    config.data_quality.id_column = "id"
    
    dmd_api = MagicMock()
    iotcore_api = MagicMock()
    
    template_chars = [
        {"name": "status", "code": "status", "type": "maindata"},
    ]
    
    row = MagicMock()
    row.asDict.return_value = {"id": "001"}  # status field is missing
    
    result = build_characteristics(template_chars, row, dmd_api, iotcore_api, config)
    
    assert result[0]["value"] is None  # Default for maindata


def test_build_characteristics_handles_iot_signals():
    """Test that build_characteristics handles iotsignal characteristics."""
    config = MagicMock()
    config.data_quality.id_column = "id"
    
    dmd_api = MagicMock()
    iotcore_api = MagicMock()
    iotcore_api.get_uids_from_tag_name.return_value = ["uid1", "uid2"]
    
    template_chars = [
        {"name": "signals", "code": "iotsignals", "type": "iotsignal"},
    ]
    
    row = MagicMock()
    row.asDict.return_value = {"id": "asset-001"}
    
    result = build_characteristics(template_chars, row, dmd_api, iotcore_api, config)
    
    assert len(result[0]["value"]) == 2
    iotcore_api.get_uids_from_tag_name.assert_called_once_with("asset-001")
