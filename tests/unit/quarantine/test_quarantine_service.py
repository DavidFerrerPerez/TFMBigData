from unittest.mock import MagicMock

from ingestion_engine.quarantine.error_codes import ErrorCode, FailureStage
from ingestion_engine.quarantine.models import QuarantineRecord
from ingestion_engine.quarantine.quarantine_service import QuarantineService


def _make_record(run_id="run-1", environment="dev", template_code="PUMP",
                 stage=FailureStage.VALIDATION, error_code=ErrorCode.REQUIRED_FIELD_MISSING, **kwargs):
    return QuarantineRecord(
        run_id=run_id,
        environment=environment,
        template_code=template_code,
        stage=stage,
        error_code=error_code,
        error_message="some error",
        asset={"id": "asset-1"},
        **kwargs,
    )


def _make_service(base_path=""):
    blob_client = MagicMock()
    service = QuarantineService(blob_client, base_path)
    return service, blob_client


# write — empty input

def test_write_returns_empty_list_when_no_records():
    service, blob_client = _make_service()
    result = service.write([])
    assert result == []


def test_write_does_not_upload_when_no_records():
    service, blob_client = _make_service()
    service.write([])
    blob_client.upload_text.assert_not_called()


# write — single record

def test_write_uploads_one_file_for_one_record():
    service, blob_client = _make_service()
    service.write([_make_record()])
    blob_client.upload_text.assert_called_once()


def test_write_returns_one_path_for_one_record():
    service, blob_client = _make_service()
    result = service.write([_make_record()])
    assert len(result) == 1


def test_write_returns_a_string_path():
    service, blob_client = _make_service()
    result = service.write([_make_record()])
    assert isinstance(result[0], str)


# grouping — same prefix merged, different prefix separated

def test_write_groups_same_prefix_into_one_file():
    service, blob_client = _make_service()
    records = [_make_record(), _make_record()]  # identical metadata → same prefix
    service.write(records)
    blob_client.upload_text.assert_called_once()


def test_write_creates_separate_files_for_different_stages():
    service, blob_client = _make_service()
    records = [
        _make_record(stage=FailureStage.VALIDATION),
        _make_record(stage=FailureStage.UPLOAD),
    ]
    service.write(records)
    assert blob_client.upload_text.call_count == 2


def test_write_creates_separate_files_for_different_templates():
    service, blob_client = _make_service()
    records = [
        _make_record(template_code="PUMP"),
        _make_record(template_code="VALVE"),
    ]
    service.write(records)
    assert blob_client.upload_text.call_count == 2


def test_write_creates_separate_files_for_different_environments():
    service, blob_client = _make_service()
    records = [
        _make_record(environment="dev"),
        _make_record(environment="prod"),
    ]
    service.write(records)
    assert blob_client.upload_text.call_count == 2


# _to_dict — enum values become plain strings

def test_to_dict_converts_stage_to_string():
    record = _make_record(stage=FailureStage.VALIDATION)
    data = QuarantineService._to_dict(record)
    assert data["stage"] == "validation"


def test_to_dict_converts_error_code_to_string():
    record = _make_record(error_code=ErrorCode.REQUIRED_FIELD_MISSING)
    data = QuarantineService._to_dict(record)
    assert data["error_code"] == "required_field_missing"


def test_to_dict_converts_failed_at_to_iso_string():
    record = _make_record()
    data = QuarantineService._to_dict(record)
    assert isinstance(data["failed_at"], str)
    assert "T" in data["failed_at"]  # basic ISO 8601 check


# _build_blob_prefix — path contains expected segments

def test_blob_prefix_contains_environment():
    service, _ = _make_service()
    record = _make_record(environment="staging")
    prefix = service._build_blob_prefix(record)
    assert "environment=staging" in prefix


def test_blob_prefix_contains_run_id():
    service, _ = _make_service()
    record = _make_record(run_id="abc-123")
    prefix = service._build_blob_prefix(record)
    assert "run_id=abc-123" in prefix


def test_blob_prefix_contains_template():
    service, _ = _make_service()
    record = _make_record(template_code="SENSOR")
    prefix = service._build_blob_prefix(record)
    assert "template=SENSOR" in prefix


def test_blob_prefix_contains_stage():
    service, _ = _make_service()
    record = _make_record(stage=FailureStage.UPLOAD)
    prefix = service._build_blob_prefix(record)
    assert "stage=upload" in prefix


def test_blob_prefix_contains_date():
    service, _ = _make_service()
    record = _make_record()
    prefix = service._build_blob_prefix(record)
    assert f"date={record.failed_at.date().isoformat()}" in prefix


def test_blob_prefix_starts_with_base_path_when_set():
    service, _ = _make_service(base_path="quarantine/raw")
    record = _make_record()
    prefix = service._build_blob_prefix(record)
    assert prefix.startswith("quarantine/raw")
