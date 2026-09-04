from datetime import datetime

from ingestion_engine.quarantine.error_codes import ErrorCode, FailureStage
from ingestion_engine.quarantine.models import QuarantineRecord


def _make_record(**kwargs):
    defaults = {
        "run_id": "run-001",
        "environment": "dev",
        "template_code": "PUMP",
        "stage": FailureStage.STANDARDIZATION,
        "error_code": ErrorCode.REQUIRED_FIELD_MISSING,
        "error_message": "Field 'id' is missing",
        "asset": {"id": "asset-1"},
    }
    defaults.update(kwargs)
    return QuarantineRecord(**defaults)


# quarantine_id

def test_quarantine_record_auto_generates_quarantine_id():
    record = _make_record()
    assert record.quarantine_id is not None
    assert len(record.quarantine_id) > 0


def test_each_record_gets_a_unique_quarantine_id():
    r1 = _make_record()
    r2 = _make_record()
    assert r1.quarantine_id != r2.quarantine_id


# failed_at

def test_quarantine_record_auto_generates_failed_at():
    record = _make_record()
    assert isinstance(record.failed_at, datetime)


def test_quarantine_record_failed_at_is_timezone_aware():
    record = _make_record()
    assert record.failed_at.tzinfo is not None


# optional fields default to None

def test_source_id_defaults_to_none():
    record = _make_record()
    assert record.source_id is None


def test_code_reference_defaults_to_none():
    record = _make_record()
    assert record.code_reference is None


def test_field_name_defaults_to_none():
    record = _make_record()
    assert record.field_name is None


# required fields are stored as-is

def test_stores_run_id():
    record = _make_record(run_id="abc-123")
    assert record.run_id == "abc-123"


def test_stores_environment():
    record = _make_record(environment="production")
    assert record.environment == "production"


def test_stores_template_code():
    record = _make_record(template_code="VALVE")
    assert record.template_code == "VALVE"


def test_stores_error_message():
    record = _make_record(error_message="Something went wrong")
    assert record.error_message == "Something went wrong"


def test_stores_asset_dict():
    asset = {"id": "x1", "name": "Pump A", "status": "active"}
    record = _make_record(asset=asset)
    assert record.asset == asset


def test_stores_optional_source_id_when_provided():
    record = _make_record(source_id="ext-99")
    assert record.source_id == "ext-99"


def test_stores_optional_code_reference_when_provided():
    record = _make_record(code_reference="TFMDFP-PumpA")
    assert record.code_reference == "TFMDFP-PumpA"
