from unittest.mock import MagicMock, patch

import pytest

from ingestion_engine.pipelines.extract_pipeline import (
    run_extraction_pipeline,
)
from ingestion_engine.pipelines.errors import PipelineExecutionError


def _make_config(templates=None, schema="public", geometry_column="geometry"):
    """Create a mock extraction config."""
    config = MagicMock()
    config.templates = templates or ["template1"]
    config.source.db_schema = schema
    config.data_quality.geometry_column = geometry_column
    config.storage.paths.raw = "raw/data"
    return config


def _make_table_mapping(mapping=None):
    """Create a mock table mapping."""
    if mapping is None:
        mapping = {"template1": ["table1"]}
    return mapping


def _make_spark():
    """Create a mock Spark session."""
    return MagicMock()


def _make_blob_client():
    """Create a mock blob client."""
    return MagicMock()


# run_extraction_pipeline tests

def test_run_extraction_pipeline_reads_and_writes_table():
    """Test that the pipeline reads a table and writes it to blob storage."""
    config = _make_config(templates=["template1"])
    table_mapping = _make_table_mapping({"template1": ["my_table"]})
    spark = _make_spark()
    blob_client = _make_blob_client()

    with patch("ingestion_engine.pipelines.extract_pipeline.read_table_from_postgres") as mock_read, \
         patch("ingestion_engine.pipelines.extract_pipeline.write_df_to_geoparquet") as mock_write:
        
        mock_df = MagicMock()
        mock_read.return_value = mock_df

        run_extraction_pipeline(config, table_mapping, spark, blob_client, "dev", "run-123")

        mock_read.assert_called_once_with("public", "my_table", "geometry", spark, "dev")
        mock_write.assert_called_once()


def test_run_extraction_pipeline_skips_template_with_no_tables():
    """Test that templates with no configured tables log an error and fail the pipeline."""
    config = _make_config(templates=["template1", "template2"])
    table_mapping = _make_table_mapping({"template1": ["table1"]})  # template2 has no tables
    spark = _make_spark()
    blob_client = _make_blob_client()

    with patch("ingestion_engine.pipelines.extract_pipeline.read_table_from_postgres") as mock_read, \
         patch("ingestion_engine.pipelines.extract_pipeline.write_df_to_geoparquet") as mock_write:
        
        mock_df = MagicMock()
        mock_read.return_value = mock_df

        # Pipeline should raise error due to missing tables for template2
        with pytest.raises(PipelineExecutionError) as exc_info:
            run_extraction_pipeline(config, table_mapping, spark, blob_client, "dev", "run-123")

        # Error should mention template2
        assert "template2" in str(exc_info.value)


def test_run_extraction_pipeline_continues_on_read_failure():
    """Test that the pipeline continues when reading a table fails."""
    config = _make_config(templates=["template1"])
    table_mapping = _make_table_mapping({"template1": ["table1", "table2"]})
    spark = _make_spark()
    blob_client = _make_blob_client()

    with patch("ingestion_engine.pipelines.extract_pipeline.read_table_from_postgres") as mock_read, \
         patch("ingestion_engine.pipelines.extract_pipeline.write_df_to_geoparquet") as mock_write:
        
        mock_df = MagicMock()
        mock_read.side_effect = [Exception("Connection failed"), mock_df]

        with pytest.raises(PipelineExecutionError) as exc_info:
            run_extraction_pipeline(config, table_mapping, spark, blob_client, "dev", "run-123")

        # Should have attempted both tables before failing
        assert mock_read.call_count == 2
        # Error message should mention the failed table
        assert "table1" in str(exc_info.value)


def test_run_extraction_pipeline_continues_on_write_failure():
    """Test that the pipeline continues when writing a table fails."""
    config = _make_config(templates=["template1"])
    table_mapping = _make_table_mapping({"template1": ["table1", "table2"]})
    spark = _make_spark()
    blob_client = _make_blob_client()

    with patch("ingestion_engine.pipelines.extract_pipeline.read_table_from_postgres") as mock_read, \
         patch("ingestion_engine.pipelines.extract_pipeline.write_df_to_geoparquet") as mock_write:
        
        mock_df = MagicMock()
        mock_read.return_value = mock_df
        mock_write.side_effect = [Exception("Storage error"), None]

        with pytest.raises(PipelineExecutionError) as exc_info:
            run_extraction_pipeline(config, table_mapping, spark, blob_client, "dev", "run-123")

        # Should have tried both tables
        assert mock_read.call_count == 2
        assert mock_write.call_count == 2


def test_run_extraction_pipeline_all_success_no_error():
    """Test that no error is raised when all tables are extracted successfully."""
    config = _make_config(templates=["template1"])
    table_mapping = _make_table_mapping({"template1": ["table1", "table2"]})
    spark = _make_spark()
    blob_client = _make_blob_client()

    with patch("ingestion_engine.pipelines.extract_pipeline.read_table_from_postgres") as mock_read, \
         patch("ingestion_engine.pipelines.extract_pipeline.write_df_to_geoparquet") as mock_write:
        
        mock_df = MagicMock()
        mock_read.return_value = mock_df

        # Should not raise any exception
        run_extraction_pipeline(config, table_mapping, spark, blob_client, "dev", "run-123")

        assert mock_read.call_count == 2
        assert mock_write.call_count == 2


def test_run_extraction_pipeline_writes_to_correct_blob_path():
    """Test that tables are written to the correct blob path with run_id."""
    config = _make_config(templates=["template1"])
    table_mapping = _make_table_mapping({"template1": ["my_table"]})
    spark = _make_spark()
    blob_client = _make_blob_client()

    with patch("ingestion_engine.pipelines.extract_pipeline.read_table_from_postgres") as mock_read, \
         patch("ingestion_engine.pipelines.extract_pipeline.write_df_to_geoparquet") as mock_write:
        
        mock_df = MagicMock()
        mock_read.return_value = mock_df

        run_extraction_pipeline(config, table_mapping, spark, blob_client, "dev", "run-456")

        # Check that write was called with correct path
        mock_write.assert_called_once()
        call_args = mock_write.call_args
        blob_path = call_args[0][2]  # Third positional argument is blob_path
        assert blob_path == "raw/data/run_id=run-456/my_table.parquet"


def test_run_extraction_pipeline_processes_multiple_templates():
    """Test that the pipeline processes all templates."""
    config = _make_config(templates=["template1", "template2"])
    table_mapping = _make_table_mapping({
        "template1": ["table1"],
        "template2": ["table2"]
    })
    spark = _make_spark()
    blob_client = _make_blob_client()

    with patch("ingestion_engine.pipelines.extract_pipeline.read_table_from_postgres") as mock_read, \
         patch("ingestion_engine.pipelines.extract_pipeline.write_df_to_geoparquet") as mock_write:
        
        mock_df = MagicMock()
        mock_read.return_value = mock_df

        run_extraction_pipeline(config, table_mapping, spark, blob_client, "dev", "run-123")

        # Should have read 2 tables (one per template)
        assert mock_read.call_count == 2


# main function tests

@patch("ingestion_engine.pipelines.extract_pipeline.load_ingestion_config")
@patch("ingestion_engine.pipelines.extract_pipeline.create_spark_session")
@patch("ingestion_engine.pipelines.extract_pipeline.configure_logging")
@patch("ingestion_engine.pipelines.extract_pipeline.validate_blob_config")
@patch("ingestion_engine.pipelines.extract_pipeline.BlobClient")
@patch("ingestion_engine.pipelines.extract_pipeline.load_table_mapping")
@patch("ingestion_engine.pipelines.extract_pipeline.run_extraction_pipeline")
@patch.dict("os.environ", {"AZURE_STORAGE_CONNECTION_STRING": "mock_connection"})
def test_main_loads_config_and_runs_pipeline(
    mock_run_pipeline,
    mock_load_mapping,
    mock_blob_client_class,
    mock_validate_blob,
    mock_configure_logging,
    mock_create_spark,
    mock_load_config,
):
    """Test that main loads config and calls the extraction pipeline."""
    from ingestion_engine.pipelines.extract_pipeline import main

    # Setup mocks
    mock_config = MagicMock()
    mock_config.available_environments = ["dev", "prod"]
    mock_config.storage.container = "my_container"
    mock_load_config.return_value = mock_config

    mock_spark = MagicMock()
    mock_create_spark.return_value = mock_spark

    mock_table_mapping = {"template1": ["table1"]}
    mock_load_mapping.return_value = mock_table_mapping

    # Call main
    main("dev", "run-123")

    # Verify calls
    mock_load_config.assert_called_once_with("config/ingestion.yaml")
    mock_create_spark.assert_called_once_with(app_name="ingestion-engine-extraction")
    mock_configure_logging.assert_called_once()
    mock_validate_blob.assert_called_once()
    mock_blob_client_class.assert_called_once()
    mock_load_mapping.assert_called_once_with("config/mappings/templates_mapping.json")
    mock_run_pipeline.assert_called_once()
    mock_spark.stop.assert_called_once()


@patch("ingestion_engine.pipelines.extract_pipeline.load_ingestion_config")
@patch("ingestion_engine.pipelines.extract_pipeline.create_spark_session")
def test_main_validates_environment(mock_create_spark, mock_load_config):
    """Test that main validates the environment."""
    from ingestion_engine.pipelines.extract_pipeline import main

    mock_config = MagicMock()
    mock_config.available_environments = ["dev", "prod"]
    mock_load_config.return_value = mock_config
    
    mock_spark = MagicMock()
    mock_create_spark.return_value = mock_spark

    with pytest.raises(ValueError) as exc_info:
        main("staging", "run-123")

    assert "Invalid environment" in str(exc_info.value)
    assert "staging" in str(exc_info.value)


@patch("ingestion_engine.pipelines.extract_pipeline.run_extraction_pipeline")
@patch("ingestion_engine.pipelines.extract_pipeline.load_table_mapping")
@patch("ingestion_engine.pipelines.extract_pipeline.BlobClient")
@patch("ingestion_engine.pipelines.extract_pipeline.validate_blob_config")
@patch("ingestion_engine.pipelines.extract_pipeline.configure_logging")
@patch("ingestion_engine.pipelines.extract_pipeline.create_spark_session")
@patch("ingestion_engine.pipelines.extract_pipeline.load_ingestion_config")
@patch.dict("os.environ", {"AZURE_STORAGE_CONNECTION_STRING": "mock_connection"})
def test_main_stops_spark_even_on_failure(
    mock_load_config,
    mock_create_spark,
    mock_configure_logging,
    mock_validate_blob,
    mock_blob_client_class,
    mock_load_mapping,
    mock_run_pipeline,
):
    """Test that spark session is stopped even if pipeline fails."""
    from ingestion_engine.pipelines.extract_pipeline import main

    mock_config = MagicMock()
    mock_config.available_environments = ["dev"]
    mock_config.storage.container = "my_container"
    mock_load_config.return_value = mock_config

    mock_spark = MagicMock()
    mock_create_spark.return_value = mock_spark

    mock_run_pipeline.side_effect = Exception("Pipeline error")

    with pytest.raises(Exception):
        main("dev", "run-123")

    # Spark should still be stopped even though pipeline failed
    mock_spark.stop.assert_called_once()
