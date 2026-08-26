import json
import pytest

from unittest.mock import MagicMock, patch, mock_open

from ingestion_engine.pipelines.standardize_pipeline import (
    configure_logging,
    load_table_mapping,
    validate_blob_config,
    process_template_tables,
    run_standardization_pipeline,
)


# configure_logging

def test_configure_logging_does_not_raise():
    configure_logging()


# load_table_mapping

def test_load_table_mapping_returns_parsed_dict():
    data = {"template1": ["table1", "table2"]}
    with patch("builtins.open", mock_open(read_data=json.dumps(data))):
        result = load_table_mapping("some/path.json")
    assert result == data


def test_load_table_mapping_empty_mapping():
    with patch("builtins.open", mock_open(read_data=json.dumps({}))):
        result = load_table_mapping("path.json")
    assert result == {}


# validate_blob_config

def test_validate_blob_config_raises_if_connection_string_is_empty():
    with pytest.raises(ValueError, match="connection string"):
        validate_blob_config("", "my-container")


def test_validate_blob_config_raises_if_connection_string_is_none():
    with pytest.raises(ValueError, match="connection string"):
        validate_blob_config(None, "my-container")


def test_validate_blob_config_raises_if_container_name_is_empty():
    with pytest.raises(ValueError, match="container name"):
        validate_blob_config("DefaultEndpointsProtocol=https;...", "")


def test_validate_blob_config_raises_if_container_name_is_none():
    with pytest.raises(ValueError, match="container name"):
        validate_blob_config("DefaultEndpointsProtocol=https;...", None)


def test_validate_blob_config_passes_when_both_values_are_set():
    validate_blob_config("DefaultEndpointsProtocol=https;...", "my-container")


# process_template_tables

@patch("ingestion_engine.pipelines.standardize_pipeline.transform_with_template_schema")
@patch("ingestion_engine.pipelines.standardize_pipeline.read_geoparquet_to_df")
def test_process_template_tables_returns_transformed_dfs(mock_read, mock_transform):
    spark = MagicMock()
    blob_client = MagicMock()
    dmdapi = MagicMock()
    dmdapi.get_template_id_by_code.return_value = 1
    dmdapi.get_template_schema_by_id.return_value = []

    ingestion_config = MagicMock()
    ingestion_config.storage.paths.raw = "raw"
    ingestion_config.data_quality.core_fields = ["id"]

    table_mapping = {"template1": ["table1", "table2"]}
    mock_read.return_value = MagicMock()
    mock_transform.return_value = MagicMock()

    result = process_template_tables(spark, blob_client, ingestion_config, table_mapping, dmdapi, "template1")

    assert len(result) == 2
    assert mock_read.call_count == 2
    assert mock_transform.call_count == 2


@patch("ingestion_engine.pipelines.standardize_pipeline.transform_with_template_schema")
@patch("ingestion_engine.pipelines.standardize_pipeline.read_geoparquet_to_df")
def test_process_template_tables_skips_tables_that_fail_to_read(mock_read, mock_transform):
    spark = MagicMock()
    blob_client = MagicMock()
    dmdapi = MagicMock()
    dmdapi.get_template_id_by_code.return_value = 1
    dmdapi.get_template_schema_by_id.return_value = []

    ingestion_config = MagicMock()
    ingestion_config.storage.paths.raw = "raw"
    ingestion_config.data_quality.core_fields = ["id"]

    table_mapping = {"template1": ["table_ok", "table_bad"]}
    mock_read.side_effect = [MagicMock(), Exception("blob not found")]
    mock_transform.return_value = MagicMock()

    result = process_template_tables(spark, blob_client, ingestion_config, table_mapping, dmdapi, "template1")

    assert len(result) == 1


@patch("ingestion_engine.pipelines.standardize_pipeline.transform_with_template_schema")
@patch("ingestion_engine.pipelines.standardize_pipeline.read_geoparquet_to_df")
def test_process_template_tables_empty_table_list_returns_empty(mock_read, mock_transform):
    dmdapi = MagicMock()
    dmdapi.get_template_id_by_code.return_value = 1
    dmdapi.get_template_schema_by_id.return_value = []

    ingestion_config = MagicMock()
    ingestion_config.storage.paths.raw = "raw"
    ingestion_config.data_quality.core_fields = ["id"]

    result = process_template_tables(MagicMock(), MagicMock(), ingestion_config, {"tmpl": []}, dmdapi, "tmpl")

    assert result == []
    mock_read.assert_not_called()


# run_standardization_pipeline

@patch.dict("os.environ", {"DMD_API_URL_DEV": "http://dmd.example.com", "DMD_API_TOKEN_DEV": "token"})
@patch("ingestion_engine.pipelines.standardize_pipeline.write_df_to_geoparquet")
@patch("ingestion_engine.pipelines.standardize_pipeline.validate_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.anonymize_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.remove_mandatory_nulls")
@patch("ingestion_engine.pipelines.standardize_pipeline.remove_duplicates")
@patch("ingestion_engine.pipelines.standardize_pipeline.fill_name")
@patch("ingestion_engine.pipelines.standardize_pipeline.unify_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.process_template_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.DMDApi")
def test_run_pipeline_processes_all_templates(
    mock_dmdapi_cls, mock_process, mock_unify, mock_fill,
    mock_dedup, mock_nulls, mock_anon, mock_validate, mock_write,
):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template1", "template2"]

    mock_process.return_value = [MagicMock()]
    mock_unify.return_value = MagicMock()
    mock_fill.return_value = MagicMock()
    mock_dedup.return_value = MagicMock()
    mock_nulls.return_value = MagicMock()
    mock_anon.return_value = MagicMock()

    run_standardization_pipeline(MagicMock(), MagicMock(), ingestion_config, {})

    assert mock_process.call_count == 2
    assert mock_unify.call_count == 2
    assert mock_write.call_count == 2


@patch.dict("os.environ", {"DMD_API_URL_DEV": "http://dmd.example.com", "DMD_API_TOKEN_DEV": "token"})
@patch("ingestion_engine.pipelines.standardize_pipeline.write_df_to_geoparquet")
@patch("ingestion_engine.pipelines.standardize_pipeline.validate_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.anonymize_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.remove_mandatory_nulls")
@patch("ingestion_engine.pipelines.standardize_pipeline.remove_duplicates")
@patch("ingestion_engine.pipelines.standardize_pipeline.fill_name")
@patch("ingestion_engine.pipelines.standardize_pipeline.unify_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.process_template_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.DMDApi")
def test_run_pipeline_skips_template_on_process_error(
    mock_dmdapi_cls, mock_process, mock_unify, mock_fill,
    mock_dedup, mock_nulls, mock_anon, mock_validate, mock_write,
):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template1"]
    mock_process.side_effect = Exception("DMD unreachable")

    run_standardization_pipeline(MagicMock(), MagicMock(), ingestion_config, {})

    mock_write.assert_not_called()


@patch.dict("os.environ", {"DMD_API_URL_DEV": "http://dmd.example.com", "DMD_API_TOKEN_DEV": "token"})
@patch("ingestion_engine.pipelines.standardize_pipeline.write_df_to_geoparquet")
@patch("ingestion_engine.pipelines.standardize_pipeline.validate_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.anonymize_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.remove_mandatory_nulls")
@patch("ingestion_engine.pipelines.standardize_pipeline.remove_duplicates")
@patch("ingestion_engine.pipelines.standardize_pipeline.fill_name")
@patch("ingestion_engine.pipelines.standardize_pipeline.unify_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.process_template_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.DMDApi")
def test_run_pipeline_skips_template_on_validation_error(
    mock_dmdapi_cls, mock_process, mock_unify, mock_fill,
    mock_dedup, mock_nulls, mock_anon, mock_validate, mock_write,
):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template1"]

    mock_process.return_value = [MagicMock()]
    mock_unify.return_value = MagicMock()
    mock_fill.return_value = MagicMock()
    mock_dedup.return_value = MagicMock()
    mock_nulls.return_value = MagicMock()
    mock_anon.return_value = MagicMock()
    mock_validate.side_effect = ValueError("duplicate IDs")

    run_standardization_pipeline(MagicMock(), MagicMock(), ingestion_config, {})

    mock_write.assert_not_called()


@patch.dict("os.environ", {"DMD_API_URL_DEV": "http://dmd.example.com", "DMD_API_TOKEN_DEV": "token"})
@patch("ingestion_engine.pipelines.standardize_pipeline.write_df_to_geoparquet")
@patch("ingestion_engine.pipelines.standardize_pipeline.validate_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.anonymize_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.remove_mandatory_nulls")
@patch("ingestion_engine.pipelines.standardize_pipeline.remove_duplicates")
@patch("ingestion_engine.pipelines.standardize_pipeline.fill_name")
@patch("ingestion_engine.pipelines.standardize_pipeline.unify_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.process_template_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.DMDApi")
def test_run_pipeline_uses_correct_environment(
    mock_dmdapi_cls, mock_process, mock_unify, mock_fill,
    mock_dedup, mock_nulls, mock_anon, mock_validate, mock_write,
):
    ingestion_config = MagicMock()
    ingestion_config.templates = []

    run_standardization_pipeline(MagicMock(), MagicMock(), ingestion_config, {}, environment="DEV")

    mock_dmdapi_cls.assert_called_once_with(
        dmd_api_url="http://dmd.example.com",
        token="token",
    )
