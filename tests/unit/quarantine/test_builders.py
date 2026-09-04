from unittest.mock import MagicMock

from ingestion_engine.quarantine.builders import build_quarantine_records_from_df
from ingestion_engine.quarantine.error_codes import ErrorCode, FailureStage


def _make_row(data: dict):
    row = MagicMock()
    row.asDict.return_value = data
    return row


def _make_df(rows: list[dict]):
    df = MagicMock()
    df.toLocalIterator.return_value = iter([_make_row(r) for r in rows])
    return df


def _build(df, *, run_id="run-1", environment="dev", template="PUMP",
           stage=FailureStage.STANDARDIZATION, error_code=ErrorCode.REQUIRED_FIELD_MISSING,
           error_message="missing field"):
    return build_quarantine_records_from_df(df, run_id, environment, template, stage, error_code, error_message)


# empty DataFrame

def test_returns_empty_list_for_empty_df():
    result = _build(_make_df([]))
    assert result == []


# record count

def test_returns_one_record_per_row():
    result = _build(_make_df([{"id": "a1"}, {"id": "a2"}, {"id": "a3"}]))
    assert len(result) == 3


# metadata is forwarded to each record

def test_sets_run_id_on_records():
    result = _build(_make_df([{"id": "a1"}]), run_id="my-run")
    assert result[0].run_id == "my-run"


def test_sets_environment_on_records():
    result = _build(_make_df([{"id": "a1"}]), environment="production")
    assert result[0].environment == "production"


def test_sets_template_code_on_records():
    result = _build(_make_df([{"id": "a1"}]), template="VALVE")
    assert result[0].template_code == "VALVE"


def test_sets_error_code_on_records():
    result = _build(_make_df([{"id": "a1"}]), error_code=ErrorCode.INVALID_GEOMETRY)
    assert result[0].error_code == ErrorCode.INVALID_GEOMETRY


def test_sets_error_message_on_records():
    result = _build(_make_df([{"id": "a1"}]), error_message="bad geometry value")
    assert result[0].error_message == "bad geometry value"


# row fields mapped to record fields

def test_uses_row_id_as_source_id():
    result = _build(_make_df([{"id": "ext-99"}]))
    assert result[0].source_id == "ext-99"


def test_source_id_is_none_when_row_has_no_id():
    result = _build(_make_df([{"name": "no id here"}]))
    assert result[0].source_id is None


def test_uses_codeReference_as_code_reference():
    result = _build(_make_df([{"id": "a1", "codeReference": "TFMDFP-PumpA"}]))
    assert result[0].code_reference == "TFMDFP-PumpA"


def test_stores_full_row_as_asset():
    row_data = {"id": "a1", "name": "Pump A", "status": "active"}
    result = _build(_make_df([row_data]))
    assert result[0].asset == row_data
