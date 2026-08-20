from pathlib import Path

import yaml

from ingestion_engine.configuration.models import IngestionConfig


def load_ingestion_config(path: str | Path) -> IngestionConfig:
    """
    Load and validate the ingestion configuration from a YAML file.
    """

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(
            f"Ingestion configuration file not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file)

    if raw_config is None:
        raise ValueError(
            f"Ingestion configuration file is empty: {path}"
        )

    return IngestionConfig.model_validate(raw_config)