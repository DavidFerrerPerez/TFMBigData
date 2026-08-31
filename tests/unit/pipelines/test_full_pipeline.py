import pytest
from unittest.mock import MagicMock, patch

from ingestion_engine.pipelines.full_pipeline import run_full_pipeline


_ENV_VARS = {
    "AZURE_STORAGE_CONNECTION_STRING": "DefaultEndpointsProtocol=https;...",
    "DMD_API_URL_DEV": "http://dmd.example.com",
    "DMD_API_TOKEN_DEV": "dmd-token",
    "IOTCORE_API_URL_DEV": "http://iotcore.example.com",
    "IOTCORE_API_TOKEN_DEV": "iotcore-token",
}


def _make_ingestion_config(environments=None):
    config = MagicMock()
    config.available_environments = environments if environments is not None else ["DEV", "PRO"]
    return config


# run_full_pipeline


@patch("ingestion_engine.pipelines.full_pipeline.load_ingestion_config")
@patch("ingestion_engine.pipelines.full_pipeline.configure_logging")
def test_run_full_pipeline_raises_for_invalid_environment(mock_logging, mock_load_config):
    mock_load_config.return_value = _make_ingestion_config(environments=["DEV"])

    with pytest.raises(ValueError, match="Invalid environment"):
        run_full_pipeline("PROD")


@patch.dict("os.environ", _ENV_VARS)
@patch("ingestion_engine.pipelines.full_pipeline.run_upload_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.run_standardization_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.run_extraction_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.create_spark_session")
@patch("ingestion_engine.pipelines.full_pipeline.BlobClient")
@patch("ingestion_engine.pipelines.full_pipeline.IOTCoreAPI")
@patch("ingestion_engine.pipelines.full_pipeline.DMDApi")
@patch("ingestion_engine.pipelines.full_pipeline.load_table_mapping")
@patch("ingestion_engine.pipelines.full_pipeline.validate_blob_config")
@patch("ingestion_engine.pipelines.full_pipeline.load_ingestion_config")
@patch("ingestion_engine.pipelines.full_pipeline.configure_logging")
def test_run_full_pipeline_calls_all_three_pipelines(
    mock_logging, mock_load_config, mock_validate, mock_load_mapping,
    mock_dmd, mock_iotcore, mock_blob, mock_spark,
    mock_extract, mock_standardize, mock_upload,
):
    mock_load_config.return_value = _make_ingestion_config()

    run_full_pipeline("DEV")

    mock_extract.assert_called_once()
    mock_standardize.assert_called_once()
    mock_upload.assert_called_once()


@patch.dict("os.environ", _ENV_VARS)
@patch("ingestion_engine.pipelines.full_pipeline.run_upload_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.run_standardization_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.run_extraction_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.create_spark_session")
@patch("ingestion_engine.pipelines.full_pipeline.BlobClient")
@patch("ingestion_engine.pipelines.full_pipeline.IOTCoreAPI")
@patch("ingestion_engine.pipelines.full_pipeline.DMDApi")
@patch("ingestion_engine.pipelines.full_pipeline.load_table_mapping")
@patch("ingestion_engine.pipelines.full_pipeline.validate_blob_config")
@patch("ingestion_engine.pipelines.full_pipeline.load_ingestion_config")
@patch("ingestion_engine.pipelines.full_pipeline.configure_logging")
def test_run_full_pipeline_runs_pipelines_in_order(
    mock_logging, mock_load_config, mock_validate, mock_load_mapping,
    mock_dmd, mock_iotcore, mock_blob, mock_spark,
    mock_extract, mock_standardize, mock_upload,
):
    mock_load_config.return_value = _make_ingestion_config()
    call_order = []
    mock_extract.side_effect = lambda *a, **kw: call_order.append("extract")
    mock_standardize.side_effect = lambda *a, **kw: call_order.append("standardize")
    mock_upload.side_effect = lambda *a, **kw: call_order.append("upload")

    run_full_pipeline("DEV")

    assert call_order == ["extract", "standardize", "upload"]


@patch.dict("os.environ", _ENV_VARS)
@patch("ingestion_engine.pipelines.full_pipeline.run_upload_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.run_standardization_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.run_extraction_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.create_spark_session")
@patch("ingestion_engine.pipelines.full_pipeline.BlobClient")
@patch("ingestion_engine.pipelines.full_pipeline.IOTCoreAPI")
@patch("ingestion_engine.pipelines.full_pipeline.DMDApi")
@patch("ingestion_engine.pipelines.full_pipeline.load_table_mapping")
@patch("ingestion_engine.pipelines.full_pipeline.validate_blob_config")
@patch("ingestion_engine.pipelines.full_pipeline.load_ingestion_config")
@patch("ingestion_engine.pipelines.full_pipeline.configure_logging")
def test_run_full_pipeline_stops_spark_even_when_a_pipeline_raises(
    mock_logging, mock_load_config, mock_validate, mock_load_mapping,
    mock_dmd, mock_iotcore, mock_blob, mock_spark,
    mock_extract, mock_standardize, mock_upload,
):
    mock_load_config.return_value = _make_ingestion_config()
    mock_extract.side_effect = RuntimeError("Postgres is down")

    with pytest.raises(RuntimeError):
        run_full_pipeline("DEV")

    mock_spark.return_value.stop.assert_called_once()


@patch.dict("os.environ", _ENV_VARS)
@patch("ingestion_engine.pipelines.full_pipeline.run_upload_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.run_standardization_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.run_extraction_pipeline")
@patch("ingestion_engine.pipelines.full_pipeline.create_spark_session")
@patch("ingestion_engine.pipelines.full_pipeline.BlobClient")
@patch("ingestion_engine.pipelines.full_pipeline.IOTCoreAPI")
@patch("ingestion_engine.pipelines.full_pipeline.DMDApi")
@patch("ingestion_engine.pipelines.full_pipeline.load_table_mapping")
@patch("ingestion_engine.pipelines.full_pipeline.validate_blob_config")
@patch("ingestion_engine.pipelines.full_pipeline.load_ingestion_config")
@patch("ingestion_engine.pipelines.full_pipeline.configure_logging")
def test_run_full_pipeline_normalises_environment_to_uppercase(
    mock_logging, mock_load_config, mock_validate, mock_load_mapping,
    mock_dmd, mock_iotcore, mock_blob, mock_spark,
    mock_extract, mock_standardize, mock_upload,
):
    mock_load_config.return_value = _make_ingestion_config(environments=["DEV"])

    run_full_pipeline("dev")

    mock_extract.assert_called_once()
