import pytest
from unittest.mock import MagicMock, patch, mock_open

from ingestion_engine.pipelines.upload_pipeline import (
    upload_asset_batch,
    run_upload_pipeline,
)


def _make_ok_response():
    response = MagicMock()
    response.ok = True
    return response


def _make_error_response(status_code=422, text="some error occurred"):
    response = MagicMock()
    response.ok = False
    response.status_code = status_code
    response.text = text
    return response


def _make_duplicate_response():
    response = MagicMock()
    response.ok = False
    response.status_code = 422
    response.text = "Duplicate Name Exception"
    return response


# upload_asset_batch

def test_upload_asset_batch_does_nothing_when_list_is_empty():
    dmd_api = MagicMock()
    upload_asset_batch([], "my_template", dmd_api, MagicMock(), "run-1", "dev")
    dmd_api.create_assets.assert_not_called()


def test_upload_asset_batch_calls_create_assets_with_the_assets():
    dmd_api = MagicMock()
    dmd_api.create_assets.return_value = _make_ok_response()
    assets = [{"name": "Asset A"}, {"name": "Asset B"}]

    upload_asset_batch(assets, "my_template", dmd_api, MagicMock(), "run-1", "dev")

    dmd_api.create_assets.assert_called_once()


def test_upload_asset_batch_clears_the_list_after_upload():
    dmd_api = MagicMock()
    dmd_api.create_assets.return_value = _make_ok_response()
    assets = [{"name": "Asset A"}]

    upload_asset_batch(assets, "my_template", dmd_api, MagicMock(), "run-1", "dev")

    assert assets == []


def test_upload_asset_batch_quarantines_assets_when_dmd_rejects_them():
    dmd_api = MagicMock()
    dmd_api.create_assets.return_value = _make_error_response(status_code=422)
    quarantine_service = MagicMock()
    assets = [{"name": "Asset A", "codeReference": "REF-1"}]

    upload_asset_batch(assets, "my_template", dmd_api, quarantine_service, "run-1", "dev")

    quarantine_service.write.assert_called_once()


def test_upload_asset_batch_skips_quarantine_on_duplicate_name_exception():
    dmd_api = MagicMock()
    dmd_api.create_assets.return_value = _make_duplicate_response()
    quarantine_service = MagicMock()
    assets = [{"name": "Asset A"}]

    with patch("ingestion_engine.pipelines.upload_pipeline.logging"):
        upload_asset_batch(assets, "my_template", dmd_api, quarantine_service, "run-1", "dev")

    quarantine_service.write.assert_not_called()


def test_upload_asset_batch_reraises_api_exception():
    dmd_api = MagicMock()
    dmd_api.create_assets.side_effect = Exception("Connection refused")
    assets = [{"name": "Asset A"}]

    with pytest.raises(Exception, match="Connection refused"):
        upload_asset_batch(assets, "my_template", dmd_api, MagicMock(), "run-1", "dev")


# run_upload_pipeline

@patch("ingestion_engine.pipelines.upload_pipeline.upload_template")
def test_run_upload_pipeline_calls_upload_template_for_each_configured_template(mock_upload_template):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template_a", "template_b"]

    run_upload_pipeline(MagicMock(), MagicMock(), ingestion_config, MagicMock(), MagicMock(), MagicMock(), "run-1", "dev")

    assert mock_upload_template.call_count == 2


@patch("ingestion_engine.pipelines.upload_pipeline.upload_template")
def test_run_upload_pipeline_does_nothing_when_no_templates_are_configured(mock_upload_template):
    ingestion_config = MagicMock()
    ingestion_config.templates = []

    run_upload_pipeline(MagicMock(), MagicMock(), ingestion_config, MagicMock(), MagicMock(), MagicMock(), "run-1", "dev")

    mock_upload_template.assert_not_called()
