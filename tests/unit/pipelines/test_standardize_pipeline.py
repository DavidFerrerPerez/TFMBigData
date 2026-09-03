import json

import pytest
from unittest.mock import MagicMock, mock_open, patch

from ingestion_engine.pipelines.errors import PipelineExecutionError
from ingestion_engine.pipelines.standardize_pipeline import (
    configure_logging,
    load_table_mapping,
    process_template_tables,
    run_standardization_pipeline,
    validate_blob_config,
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
    dmdapi.get_template_metadata.return_value = {"id": 1}
    dmdapi.get_template_schema_by_id.return_value = []

    ingestion_config = MagicMock()
    ingestion_config.storage.paths.raw = "raw"
    ingestion_config.data_quality.core_fields = ["id"]

    table_mapping = {"template1": ["table1", "table2"]}
    mock_read.return_value = MagicMock()
    mock_transform.return_value = MagicMock()

    result = process_template_tables(spark, blob_client, ingestion_config, table_mapping, dmdapi, "template1", "2024-01-15T10:30:45.123456", {}, 12)

    assert len(result) == 2
    assert mock_read.call_count == 2
    assert mock_transform.call_count == 2


@patch("ingestion_engine.pipelines.standardize_pipeline.transform_with_template_schema")
@patch("ingestion_engine.pipelines.standardize_pipeline.read_geoparquet_to_df")
def test_process_template_tables_skips_tables_that_fail_to_read(mock_read, mock_transform):
    spark = MagicMock()
    blob_client = MagicMock()
    dmdapi = MagicMock()
    dmdapi.get_template_metadata.return_value = {"id": 1}
    dmdapi.get_template_schema_by_id.return_value = []

    ingestion_config = MagicMock()
    ingestion_config.storage.paths.raw = "raw"
    ingestion_config.data_quality.core_fields = ["id"]

    table_mapping = {"template1": ["table_ok", "table_bad"]}
    mock_read.side_effect = [MagicMock(), Exception("blob not found")]
    mock_transform.return_value = MagicMock()

    with pytest.raises(Exception, match="blob not found"):
        process_template_tables(spark, blob_client, ingestion_config, table_mapping, dmdapi, "template1", "2024-01-15T10:30:45.123456", {}, 12)


@patch("ingestion_engine.pipelines.standardize_pipeline.transform_with_template_schema")
@patch("ingestion_engine.pipelines.standardize_pipeline.read_geoparquet_to_df")
def test_process_template_tables_empty_table_list_returns_empty(mock_read, mock_transform):
    dmdapi = MagicMock()
    dmdapi.get_template_metadata.return_value = {"id": 1}
    dmdapi.get_template_schema_by_id.return_value = []

    ingestion_config = MagicMock()
    ingestion_config.storage.paths.raw = "raw"
    ingestion_config.data_quality.core_fields = ["id"]

    with pytest.raises(ValueError, match="No source tables configured"):
        process_template_tables(MagicMock(), MagicMock(), ingestion_config, {"tmpl": []}, dmdapi, "tmpl", "2024-01-15T10:30:45.123456", {}, 12)

    mock_read.assert_not_called()


# run_standardization_pipeline

@patch("ingestion_engine.pipelines.standardize_pipeline.build_quarantine_records_from_df")
@patch("ingestion_engine.pipelines.standardize_pipeline.process_template_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.unify_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.fill_name")
@patch("ingestion_engine.pipelines.standardize_pipeline.anonymize_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.validate_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.write_df_to_geoparquet")
@patch("builtins.open", mock_open(read_data="{}"))
def test_run_pipeline_processes_all_templates(mock_write, mock_validate, mock_anon, mock_fill, mock_unify, mock_process, mock_quarantine):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template1", "template2"]

    mock_process.return_value = [MagicMock()]
    mock_unify.return_value = MagicMock()
    mock_fill.return_value = MagicMock()
    mock_anon.return_value = MagicMock()
    mock_validate.return_value = (MagicMock(), MagicMock())

    run_standardization_pipeline(MagicMock(), MagicMock(), ingestion_config, {}, MagicMock(), MagicMock(), "2024-01-15T10:30:45.123456", "dev")

    assert mock_process.call_count == 2
    assert mock_unify.call_count == 2
    assert mock_write.call_count == 2


@patch("ingestion_engine.pipelines.standardize_pipeline.build_quarantine_records_from_df")
@patch("ingestion_engine.pipelines.standardize_pipeline.process_template_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.unify_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.fill_name")
@patch("ingestion_engine.pipelines.standardize_pipeline.anonymize_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.validate_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.write_df_to_geoparquet")
@patch("builtins.open", mock_open(read_data="{}"))
def test_run_pipeline_skips_template_on_process_error(mock_write, mock_validate, mock_anon, mock_fill, mock_unify, mock_process, mock_quarantine):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template1"]
    mock_process.side_effect = Exception("DMD unreachable")

    with pytest.raises(PipelineExecutionError, match="DMD unreachable"):
        run_standardization_pipeline(MagicMock(), MagicMock(), ingestion_config, {}, MagicMock(), MagicMock(), "2024-01-15T10:30:45.123456", "dev")

    mock_write.assert_not_called()


@patch("ingestion_engine.pipelines.standardize_pipeline.build_quarantine_records_from_df")
@patch("ingestion_engine.pipelines.standardize_pipeline.process_template_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.unify_tables")
@patch("ingestion_engine.pipelines.standardize_pipeline.fill_name")
@patch("ingestion_engine.pipelines.standardize_pipeline.anonymize_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.validate_dataframe")
@patch("ingestion_engine.pipelines.standardize_pipeline.write_df_to_geoparquet")
@patch("builtins.open", mock_open(read_data="{}"))
def test_run_pipeline_skips_template_on_validation_error(mock_write, mock_validate, mock_anon, mock_fill, mock_unify, mock_process, mock_quarantine):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template1"]

    mock_process.return_value = [MagicMock()]
    mock_unify.return_value = MagicMock()
    mock_fill.return_value = MagicMock()
    mock_anon.return_value = MagicMock()
    mock_validate.side_effect = ValueError("duplicate IDs")

    with pytest.raises(PipelineExecutionError, match="duplicate IDs"):
        run_standardization_pipeline(MagicMock(), MagicMock(), ingestion_config, {}, MagicMock(), MagicMock(), "2024-01-15T10:30:45.123456", "dev")

    mock_write.assert_not_called()


@patch("ingestion_engine.pipelines.standardize_pipeline.process_template_tables")
@patch("builtins.open", mock_open(read_data="{}"))
def test_run_pipeline_forwards_dmdapi_to_process_template_tables(mock_process):
    ingestion_config = MagicMock()
    ingestion_config.templates = ["template1"]
    mock_process.side_effect = Exception("stop early")

    dmdapi = MagicMock()

    with pytest.raises(PipelineExecutionError, match="stop early"):
        run_standardization_pipeline(MagicMock(), MagicMock(), ingestion_config, {}, dmdapi, MagicMock(), "2024-01-15T10:30:45.123456", "dev")

    assert mock_process.call_args[0][4] is dmdapi