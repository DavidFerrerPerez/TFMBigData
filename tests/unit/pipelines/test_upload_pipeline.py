from unittest.mock import MagicMock, patch, mock_open

from ingestion_engine.pipelines.upload_pipeline import (
    upload_asset_batch,
    _write_failed_assets,
    run_upload_pipeline,
)


def _make_response(text="OK"):
    response = MagicMock()
    response.text = text
    return response


# upload_asset_batch

def test_upload_asset_batch_does_nothing_when_list_is_empty():
    dmd_api = MagicMock()
    upload_asset_batch([], "my_template", dmd_api)
    dmd_api.create_assets.assert_not_called()


def test_upload_asset_batch_calls_create_assets_with_the_assets():
    dmd_api = MagicMock()
    dmd_api.create_assets.return_value = _make_response("OK")
    assets = [{"name": "Asset A"}, {"name": "Asset B"}]

    upload_asset_batch(assets, "my_template", dmd_api)

    dmd_api.create_assets.assert_called_once()


def test_upload_asset_batch_clears_the_list_after_upload():
    dmd_api = MagicMock()
    dmd_api.create_assets.return_value = _make_response("OK")
    assets = [{"name": "Asset A"}]

    upload_asset_batch(assets, "my_template", dmd_api)

    assert assets == []


def test_upload_asset_batch_writes_failed_assets_when_response_has_error():
    dmd_api = MagicMock()
    dmd_api.create_assets.return_value = _make_response("some error occurred")
    assets = [{"name": "Asset A"}]

    with patch("ingestion_engine.pipelines.upload_pipeline._write_failed_assets") as mock_write:
        upload_asset_batch(assets, "my_template", dmd_api)

    mock_write.assert_called_once()


def test_upload_asset_batch_skips_write_on_duplicate_name_exception():
    dmd_api = MagicMock()
    dmd_api.create_assets.return_value = _make_response("error: Duplicate Name Exception")
    assets = [{"name": "Asset A"}]

    with patch("ingestion_engine.pipelines.upload_pipeline._write_failed_assets") as mock_write:
        upload_asset_batch(assets, "my_template", dmd_api)

    mock_write.assert_not_called()


def test_upload_asset_batch_handles_api_exception_without_crashing():
    dmd_api = MagicMock()
    dmd_api.create_assets.side_effect = Exception("Connection refused")
    assets = [{"name": "Asset A"}]

    # Should not raise
    upload_asset_batch(assets, "my_template", dmd_api)


# _write_failed_assets

def test_write_failed_assets_includes_each_asset_name_in_file():
    assets = [{"name": "Pump A"}, {"name": "Valve B"}]
    response = "500 Internal Server Error"

    with patch("builtins.open", mock_open()) as mock_file:
        _write_failed_assets("my_template", assets, response)
        handle = mock_file()
        written = "".join(c.args[0] for c in handle.write.call_args_list)

    assert "Pump A" in written
    assert "Valve B" in written
    assert response in written


def test_write_failed_assets_uses_unknown_for_assets_without_a_name():
    assets = [{}]

    with patch("builtins.open", mock_open()) as mock_file:
        _write_failed_assets("my_template", assets, "error")
        handle = mock_file()
        written = "".join(c.args[0] for c in handle.write.call_args_list)

    assert "unknown" in written


# run_upload_pipeline

@patch("ingestion_engine.pipelines.upload_pipeline.upload_template")
def test_run_upload_pipeline_calls_upload_template_for_each_configured_template(mock_upload_template):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template_a", "template_b"]

    run_upload_pipeline(MagicMock(), MagicMock(), ingestion_config, MagicMock(), MagicMock())

    assert mock_upload_template.call_count == 2


@patch("ingestion_engine.pipelines.upload_pipeline.upload_template")
def test_run_upload_pipeline_does_nothing_when_no_templates_are_configured(mock_upload_template):
    ingestion_config = MagicMock()
    ingestion_config.templates = []

    run_upload_pipeline(MagicMock(), MagicMock(), ingestion_config, MagicMock(), MagicMock())

    mock_upload_template.assert_not_called()
