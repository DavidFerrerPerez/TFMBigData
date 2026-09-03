import os
import logging
import json

from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.configuration.loader import load_ingestion_config, load_table_mapping
from ingestion_engine.transformation.table_unificator import unify_tables
from ingestion_engine.dmd.dmd_api import DMDApi
from ingestion_engine.transformation.column_caster import transform_with_template_schema
from ingestion_engine.storage.geoparquet_reader import read_geoparquet_to_df
from ingestion_engine.transformation.name_validator import fill_name
from ingestion_engine.transformation.anonymization import anonymize_dataframe
from ingestion_engine.validation.complete_validation import validate_dataframe
from ingestion_engine.storage.geoparquet_writer import write_df_to_geoparquet
from ingestion_engine.logging.config import configure_logging
from ingestion_engine.spark.session import create_spark_session
from ingestion_engine.configuration.validation import validate_blob_config
from ingestion_engine.quarantine.builders import build_quarantine_records_from_df
from ingestion_engine.storage.path_utils import run_id_to_path
from ingestion_engine.transformation.geometry_caster import cast_geometry
from ingestion_engine.pipelines.errors import PipelineExecutionError, QuarantineThresholdExceededError
from ingestion_engine.pipelines.metrics import TemplateCounts
from ingestion_engine.quarantine.error_codes import ErrorCode, FailureStage
from ingestion_engine.quarantine.quarantine_service import QuarantineService


def process_template_tables(spark, blob_client: BlobClient, ingestion_config, table_mapping, dmdapi, template: str, run_id: str, characteristics_mapping: dict, template_id: int) -> list:
    """
    Process the tables for a given template.

    Args:
        spark: The Spark session.
        blob_client (BlobClient): The blob client for accessing storage.
        ingestion_config: The ingestion configuration.
        table_mapping: The table mapping for templates.
        dmdapi: The DMD API client.
        template (str): The template name.

    Returns:
        list: A list of DataFrames translated to company standard schema for the template.
    """

    tables = table_mapping.get(template)

    if not tables:
        raise ValueError(f"No source tables configured for template '{template}'.")

    source_tables = []

    template_schema = dmdapi.get_template_schema_by_id(template_id)

    if not isinstance(template_schema, list):
        raise TypeError(f"Invalid DMD schema returned for template '{template}'.")

    for table in table_mapping[template]:

        logging.debug(f"Reading table {table} from blob storage for template {template}.")

        try:
            run_id_path = run_id_to_path(run_id)
            df = read_geoparquet_to_df(spark, blob_client, f"{ingestion_config.storage.paths.raw}/run_id={run_id_path}/{table}.parquet")

        except Exception as e:
            logging.error(f"Error reading table {table} from blob storage: {e}")
            raise e

        transformed_df = transform_with_template_schema(df, ingestion_config.data_quality.core_fields, template_schema, characteristics_mapping)

        source_tables.append(transformed_df)

        logging.debug(f"Table {table} for template {template} read and transformed successfully: size is {transformed_df.count()} rows.")

    if not source_tables:
        raise ValueError(f"No source DataFrames were produced for template '{template}'.")

    return source_tables


def run_standardization_pipeline(spark, blob_client: BlobClient, ingestion_config, table_mapping, dmdapi, quarantine_service: QuarantineService, run_id: str, environment: str):
    """
    Runs the standardization pipeline for the given ingestion configuration and table mapping.

    Args:
        spark: The Spark session.
        blob_client (BlobClient): The blob client for accessing storage.
        ingestion_config: The ingestion configuration.
        table_mapping: The table mapping for templates.
        run_id (str): The unique identifier for the ingestion run.
        environment (str, optional): The environment (default is "DEV").
    """

    failures = []

    with open("config/mappings/characteristics_mapping.json", "r", encoding="utf-8") as f:
            characteristics_mapping = json.load(f)

    for template in ingestion_config.templates:
        logging.info(f"Standardizing template '{template}'.")
        quarantine_records = []
        counts = TemplateCounts()

        try:
            template_metadata = dmdapi.get_template_metadata(template)

            source_tables = process_template_tables(spark, blob_client, ingestion_config, table_mapping, dmdapi, template, run_id, characteristics_mapping, template_metadata.get("id"))

            unified_df = unify_tables(spark, source_tables)
            df_with_name = fill_name(unified_df)
            df_geom_casted = cast_geometry(
                df_with_name,
                template_metadata.get("geometry_type"),
                ingestion_config.data_quality.geometry_column,
            )
            df_anonymized = anonymize_dataframe(df_geom_casted, ingestion_config)
            valid_df, rejected_validation_df = validate_dataframe(df_anonymized, ingestion_config)

            if not rejected_validation_df.isEmpty():
                rejected_count = rejected_validation_df.count()
                logging.warning(f"Rejected {rejected_count} rows during final validation for template '{template}'.")
                counts.add_quarantined(rejected_count)

                quarantine_records.extend(
                    build_quarantine_records_from_df(
                        rejected_validation_df,
                        run_id=run_id,
                        environment=environment,
                        template=template,
                        stage=FailureStage.VALIDATION,
                        error_code=ErrorCode.INVALID_TYPE,
                        error_message="Asset failed final validation.",
                    )
                )

            counts.add_written(valid_df.count())

            run_id_path = run_id_to_path(run_id)

            write_df_to_geoparquet(
                valid_df,
                blob_client,
                f"{ingestion_config.storage.paths.standard}/run_id={run_id_path}/{template}.parquet",
            )

            if counts.exceeds_threshold(ingestion_config.quality_threshold.max_quarantine_ratio):
                raise QuarantineThresholdExceededError(
                    template, counts.quarantined, counts.total, ingestion_config.quality_threshold.max_quarantine_ratio
                )

            logging.info(
                f"Template '{template}' standardized successfully "
                f"({counts.written} written, {counts.quarantined} quarantined)."
            )

        except Exception as e:
            logging.exception(f"Standardization failed for template '{template}'.")
            failures.append(f"template={template}: {e}")

        finally:
            if quarantine_records:
                try:
                    quarantine_service.write(quarantine_records)
                    logging.info(f"Wrote {len(quarantine_records)} quarantine records for template '{template}'.")
                except Exception as e:
                    logging.exception(f"Could not persist quarantine records for template '{template}'.")
                    failures.append(f"template={template}, quarantine: {e}")

    if failures:
        raise PipelineExecutionError("standardization", failures)


def main(environment: str, run_id: str):

    ingestion_config = load_ingestion_config("config/ingestion.yaml")

    if environment not in ingestion_config.available_environments:
        raise ValueError(f"Invalid environment '{environment}'. Available environments: {ingestion_config.available_environments}")

    logging.info(f"Starting the standardization pipeline for environment '{environment}'... run_id: {run_id}")

    configure_logging()

    table_mapping = load_table_mapping("config/mappings/templates_mapping.json")

    spark = create_spark_session(app_name="ingestion-engine-standardization")

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = ingestion_config.storage.container

    validate_blob_config(connection_string, container_name)

    dmdapi = DMDApi(
        dmd_api_url=os.environ[f'DMD_API_URL_{environment}'],
        token=os.environ[f'DMD_API_TOKEN_{environment}']
    )

    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    quarantine_service = QuarantineService(
        blob_client=blob_client,
        base_path=ingestion_config.storage.paths.quarantine,
    )

    try:
        run_standardization_pipeline(spark, blob_client, ingestion_config, table_mapping, dmdapi, quarantine_service, run_id, environment)
    finally:
        spark.stop()

    logging.info("Standardization pipeline completed successfully.")