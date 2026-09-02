from unittest.mock import MagicMock, patch, call
import pytest

from ingestion_engine.cli import run_pipeline, main


# run_pipeline tests

def test_run_pipeline_extract_calls_extract_pipeline():
    """Test that run_pipeline calls extract_pipeline when stage is 'extract'."""
    with patch("ingestion_engine.cli.extract_pipeline.main") as mock_extract:
        run_pipeline("extract", "dev", "run-123")
        
        mock_extract.assert_called_once_with(environment="dev", run_id="run-123")


def test_run_pipeline_standardize_calls_standardize_pipeline():
    """Test that run_pipeline calls standardize_pipeline when stage is 'standardize'."""
    with patch("ingestion_engine.cli.standardize_pipeline.main") as mock_standardize:
        run_pipeline("standardize", "prod", "run-456")
        
        mock_standardize.assert_called_once_with(environment="prod", run_id="run-456")


def test_run_pipeline_upload_calls_upload_pipeline():
    """Test that run_pipeline calls upload_pipeline when stage is 'upload'."""
    with patch("ingestion_engine.cli.upload_pipeline.main") as mock_upload:
        run_pipeline("upload", "dev", "run-789")
        
        mock_upload.assert_called_once_with(environment="dev", run_id="run-789")


def test_run_pipeline_invalid_stage_does_nothing():
    """Test that run_pipeline doesn't call any pipeline for invalid stage."""
    with patch("ingestion_engine.cli.extract_pipeline.main") as mock_extract, \
         patch("ingestion_engine.cli.standardize_pipeline.main") as mock_standardize, \
         patch("ingestion_engine.cli.upload_pipeline.main") as mock_upload:
        
        run_pipeline("invalid", "dev", "run-123")
        
        mock_extract.assert_not_called()
        mock_standardize.assert_not_called()
        mock_upload.assert_not_called()


# main function tests

@patch("ingestion_engine.cli.run_pipeline")
@patch("ingestion_engine.cli.load_ingestion_config")
@patch("sys.argv", ["cli.py", "run", "--stage", "extract", "--environment", "dev"])
def test_main_parses_extract_command(mock_load_config, mock_run_pipeline):
    """Test that main parses extract command correctly."""
    mock_config = MagicMock()
    mock_config.available_environments = ["dev", "prod"]
    mock_load_config.return_value = mock_config
    
    main()
    
    # run_pipeline should be called with extract stage
    call_args = mock_run_pipeline.call_args
    assert call_args[0][0] == "extract"
    assert call_args[0][1] == "dev"
    # run_id should be auto-generated
    assert len(call_args[0][2]) > 0


@patch("ingestion_engine.cli.run_pipeline")
@patch("ingestion_engine.cli.load_ingestion_config")
@patch("sys.argv", ["cli.py", "run", "--stage", "standardize", "--environment", "prod"])
def test_main_parses_standardize_command(mock_load_config, mock_run_pipeline):
    """Test that main parses standardize command correctly."""
    mock_config = MagicMock()
    mock_config.available_environments = ["dev", "prod"]
    mock_load_config.return_value = mock_config
    
    main()
    
    call_args = mock_run_pipeline.call_args
    assert call_args[0][0] == "standardize"
    assert call_args[0][1] == "prod"


@patch("ingestion_engine.cli.run_pipeline")
@patch("ingestion_engine.cli.load_ingestion_config")
@patch("sys.argv", ["cli.py", "run", "--stage", "upload", "--environment", "dev", "--run-id", "custom-run-id"])
def test_main_uses_custom_run_id(mock_load_config, mock_run_pipeline):
    """Test that main uses custom run_id when provided."""
    mock_config = MagicMock()
    mock_config.available_environments = ["dev", "prod"]
    mock_load_config.return_value = mock_config
    
    main()
    
    call_args = mock_run_pipeline.call_args
    assert call_args[0][2] == "custom-run-id"


@patch("ingestion_engine.cli.load_ingestion_config")
@patch("sys.argv", ["cli.py", "run", "--stage", "extract", "--environment", "staging"])
def test_main_rejects_invalid_environment(mock_load_config):
    """Test that main rejects invalid environment."""
    mock_config = MagicMock()
    mock_config.available_environments = ["dev", "prod"]
    mock_load_config.return_value = mock_config
    
    with pytest.raises(SystemExit):
        main()


@patch("ingestion_engine.cli.load_ingestion_config")
@patch("sys.argv", ["cli.py", "run", "--stage", "invalid"])
def test_main_rejects_invalid_stage(mock_load_config):
    """Test that main rejects invalid stage."""
    mock_config = MagicMock()
    mock_config.available_environments = ["dev", "prod"]
    mock_load_config.return_value = mock_config
    
    with pytest.raises(SystemExit):
        main()


@patch("ingestion_engine.cli.run_pipeline")
@patch("ingestion_engine.cli.load_ingestion_config")
@patch("sys.argv", ["cli.py", "run", "--stage", "extract", "--environment", "dev"])
def test_main_loads_config_before_parsing(mock_load_config, mock_run_pipeline):
    """Test that main loads config before parsing arguments."""
    mock_config = MagicMock()
    mock_config.available_environments = ["dev", "prod"]
    mock_load_config.return_value = mock_config
    
    main()
    
    # load_ingestion_config should be called
    mock_load_config.assert_called_once_with("config/ingestion.yaml")
