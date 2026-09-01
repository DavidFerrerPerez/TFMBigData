import argparse
import sys
import logging

from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.pipelines import extract_pipeline, standardize_pipeline, upload_pipeline

def run_pipeline(stage: str, environment: str) -> None:
    if stage == "extract":
        extract_pipeline.main(environment=environment)
    elif stage == "standardize":
        standardize_pipeline.main(environment=environment)
    elif stage == "upload":
        upload_pipeline.main(environment=environment)


def main() -> None:

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )

    extraction_config = load_ingestion_config("config/ingestion.yaml")

    parser = argparse.ArgumentParser(description="Ingestion engine")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--stage", required=True, choices=["extract", "standardize", "upload"])
    parser.add_argument("--environment", required=True, choices=extraction_config.available_environments)

    args = parser.parse_args()

    if args.command == "run":
        run_pipeline(stage=args.stage, environment=args.environment)