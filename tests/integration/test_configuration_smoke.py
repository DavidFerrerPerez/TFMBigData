from pathlib import Path

from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.configuration.models import IngestionConfig


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "ingestion.yaml"
EXAMPLE_CONFIG_PATH = PROJECT_ROOT / "config" / "ingestion.example.yaml"


def test_ingestion_configuration_can_be_loaded():
    config_path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH

    config = load_ingestion_config(config_path)

    assert isinstance(config, IngestionConfig)
    assert config.available_environments
    assert config.source.db_schema
    assert config.templates
    assert config.storage.container
    assert config.storage.paths.raw
    assert config.storage.paths.standard
    assert config.storage.paths.quarantine
    assert config.data_quality.core_fields
    assert config.data_quality.id_column
    assert config.data_quality.geometry_column
    assert config.pseudonymization is not None
    assert config.dmd.batch_size > 0
    assert 0 <= config.quality_threshold.max_quarantine_ratio <= 1