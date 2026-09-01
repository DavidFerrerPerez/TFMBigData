import argparse
import logging
import sys
from uuid import uuid4

from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.pipelines import extract_pipeline, standardize_pipeline, upload_pipeline


def run_pipeline(stage: str, environment: str, run_id: str) -> None:
    if stage == "extract":
        extract_pipeline.main(environment=environment, run_id=run_id)
    elif stage == "standardize":
        standardize_pipeline.main(environment=environment, run_id=run_id)
    elif stage == "upload":
        upload_pipeline.main(environment=environment, run_id=run_id)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
        force=True,
    )

    ingestion_config = load_ingestion_config("config/ingestion.yaml")

    parser = argparse.ArgumentParser(description="Ingestion engine")
    parser.add_argument("command", choices=["run"])
    parser.add_argument("--stage", required=True, choices=["extract", "standardize", "upload"])
    parser.add_argument("--environment", required=True, choices=ingestion_config.available_environments)
    parser.add_argument("--run-id", default=str(uuid4()))

    args = parser.parse_args()

    if args.command == "run":
        run_pipeline(args.stage, args.environment, args.run_id)