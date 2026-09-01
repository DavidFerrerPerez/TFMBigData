import logging
import os
import sys
import json

from sedona.spark import SedonaContext
from uuid import uuid4

from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.configuration.validation import validate_blob_config
from ingestion_engine.dmd.asset_builder import build_asset
from ingestion_engine.dmd.characteristics import create_characteristics_list, build_characteristics
from ingestion_engine.dmd.dmd_api import DMDApi
from ingestion_engine.iotcore.iotcore_api import IOTCoreAPI
from ingestion_engine.logging.config import configure_logging
from ingestion_engine.spark.session import create_spark_session
from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.storage.geoparquet_reader import read_geoparquet_to_df
from ingestion_engine.quarantine.builders import build_quarantine_records_from_df, build_upload_quarantine_records
from ingestion_engine.quarantine.error_codes import ErrorCode, FailureStage
from ingestion_engine.quarantine.quarantine_service import QuarantineService
from ingestion_engine.quarantine.models import QuarantineRecord


def upload_asset_batch(asset_list: list[dict], template: str, dmd_api: DMDApi, quarantine_service: QuarantineService, run_id: str, environment: str) -> None:
    if not asset_list:
        return

    try:
        response = dmd_api.create_assets(asset_list)
    except Exception as e:
        logging.exception(f"Error communicating with DMD while uploading template '{template}': {e}")
        raise

    if response.ok:
        asset_list.clear()
        return

    if "Duplicate Name Exception" in response.text:
        logging.warning(f"Duplicate assets detected for template '{template}'.")
        asset_list.clear()
        return

    if 400 <= response.status_code < 500:
        records = build_upload_quarantine_records(asset_list, template, run_id, environment, response)

        quarantine_service.write(records)

        logging.warning(f"Quarantined {len(records)} assets rejected by DMD for template '{template}'.")
        asset_list.clear()
        return

    raise RuntimeError(
        f"DMD upload failed for template '{template}' "
        f"with HTTP {response.status_code}: {response.text}"
    )


def upload_template(spark: SedonaContext, blob_client: BlobClient, template: str, ingestion_config, dmd_api: DMDApi, iotcore_api: IOTCoreAPI, quarantine_service: QuarantineService, run_id: str, environment: str) -> None:
    """
    Read, prepare and upload all assets associated with a DMD template.

    Args:
        spark (SedonaContext): The Spark session.
        blob_client (BlobClient): The blob client for accessing storage.
        template (str): The template name.
        ingestion_config: The ingestion configuration.
        dmd_api (DMDApi): The DMD API client.
        iotcore_api (IOTCoreAPI): The IoT Core API client.
    """
    logging.info(f"Uploading template {template}...")

    try:
        df_assets = read_geoparquet_to_df(spark, blob_client, f"{ingestion_config.storage.paths.standard}/{template}.parquet")
    except Exception as e:
        logging.exception(f"Error reading template '{template}' from blob storage: {e}")
        return

    try:
        template_metadata = dmd_api.get_template_metadata(template)
        template_schema = dmd_api.get_template_schema_by_id(template_metadata.get("id"))
    except Exception as e:
        logging.exception(f"Error retrieving DMD schema for template '{template}': {e}")
        return

    template_characteristics_list = create_characteristics_list(template_schema)

    asset_list = []
    quarantine_records = []

    for row in df_assets.toLocalIterator():
        try:
            row_specific_characteristics = build_characteristics(template_characteristics_list, row, dmd_api, iotcore_api)

            asset = build_asset(
                row,
                row_specific_characteristics,
                template_metadata,
                ingestion_config.main_hierarchy_parent,
                ingestion_config.data_quality.geometry_column,
            )

        except Exception as e:
            payload = row.asDict(recursive=True)

            record = QuarantineRecord(
                run_id=run_id,
                environment=environment,
                template_code=template,
                source_id=str(payload.get("id")) if payload.get("id") is not None else None,
                code_reference=payload.get("codeReference"),
                stage=FailureStage.UPLOAD,
                error_code=ErrorCode.DMD_REJECTED_ASSET,
                error_message=str(e),
                asset=payload,
            )

            quarantine_records.append(record)

            logging.warning(f"Asset quarantined while building template '{template}': {e}")
            continue

        asset_list.append(asset)

        if len(asset_list) >= ingestion_config.batch_size:
            upload_asset_batch(asset_list, template, dmd_api, quarantine_service, run_id, environment)

    if asset_list:
        upload_asset_batch(asset_list, template, dmd_api, quarantine_service, run_id, environment)

    if quarantine_records:
        quarantine_service.write(quarantine_records)

    logging.info(f"Template {template} uploaded successfully.")


def run_upload_pipeline(spark: SedonaContext, blob_client: BlobClient, ingestion_config, dmd_api: DMDApi, iotcore_api: IOTCoreAPI, quarantine_service: QuarantineService, run_id: str, environment: str) -> None:
    """
    Execute the upload pipeline for every configured template.
    """
    for template in ingestion_config.templates:
        upload_template(spark, blob_client, template, ingestion_config, dmd_api, iotcore_api, quarantine_service, run_id, environment)


def main(environment: str) -> None:
    
    configure_logging()

    environment = environment.upper()

    run_id = str(uuid4())

    logging.info(f"Starting the upload pipeline for environment '{environment}'... run_id: {run_id}")

    ingestion_config = load_ingestion_config("config/ingestion.yaml")

    if environment not in ingestion_config.available_environments:
        raise ValueError(f"Invalid environment '{environment}'. Available environments: {ingestion_config.available_environments}")

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = ingestion_config.storage.container

    validate_blob_config(connection_string, container_name)

    dmd_api = DMDApi(
        dmd_api_url=os.environ[f"DMD_API_URL_{environment}"],
        token=os.environ[f"DMD_API_TOKEN_{environment}"]
    )

    iotcore_api = IOTCoreAPI(
        iotcore_api_url=os.environ[f"IOTCORE_API_URL_{environment}"],
        token=os.environ[f"IOTCORE_API_TOKEN_{environment}"],
        driver=os.environ.get(f"IOTCORE_API_DRIVER_{environment}")
    )

    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name
    )

    quarantine_service = QuarantineService(
        blob_client=blob_client,
        base_path=ingestion_config.storage.paths.quarantine,
    )

    spark = create_spark_session(app_name="ingestion-engine-upload")

    try:
        run_upload_pipeline(spark, blob_client, ingestion_config, dmd_api, iotcore_api, quarantine_service, run_id, environment)
    finally:
        spark.stop()

    logging.info("Upload pipeline completed successfully.")