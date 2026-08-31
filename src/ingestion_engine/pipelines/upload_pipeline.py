import logging
import os
import sys

from sedona.spark import SedonaContext

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


def upload_asset_batch(asset_list: list[dict], template: str, dmd_api: DMDApi) -> None:
    """
    Upload a batch of assets to DMD.

    Args:
        asset_list (list[dict]): Assets to upload.
        template (str): Template name used for logging and error output.
        dmd_api (DMDApi): DMD API client.
    """
    if not asset_list:
        return

    try:
        response = dmd_api.create_assets(asset_list)

        print(f"Response for template '{template}': {response}")

        if "error" in str(response.text).lower() and "Duplicate Name Exception" not in str(response.text):
            logging.warning(f"Error detected in response for template '{template}'. Writing failed assets to file.")
            _write_failed_assets(template, asset_list, response.text)

    except Exception as e:
        logging.exception(f"Error uploading batch for template '{template}': {e}")

    finally:
        asset_list.clear()


def _write_failed_assets(template: str, assets: list[dict], response) -> None:
    """
    Write failed asset names and their API response to a file.

    Args:
        template (str): Template name used for the filename.
        assets (list[dict]): List of assets that failed to upload.
        response: The API response that indicates the failure.
    """
    with open(f"{template}_failed_assets.txt", "a", encoding="utf-8") as file:
        for asset in assets:
            file.write(f"{asset.get('name', 'unknown')}: {response}\n")


def upload_template(spark: SedonaContext, blob_client: BlobClient, template: str, ingestion_config, dmd_api: DMDApi, iotcore_api: IOTCoreAPI) -> None:
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

    for row in df_assets.toLocalIterator():
        row_specific_characteristics = build_characteristics(template_characteristics_list, row, dmd_api, iotcore_api)

        asset = build_asset(row, row_specific_characteristics, template_metadata, ingestion_config.main_hierarchy_parent, ingestion_config.data_quality.geometry_column)

        print(asset)

        asset_list.append(asset)

        if len(asset_list) >= ingestion_config.batch_size:
            upload_asset_batch(asset_list, template, dmd_api)

    if asset_list:
        upload_asset_batch(asset_list, template, dmd_api)

    logging.info(f"Template {template} uploaded successfully.")


def run_upload_pipeline(spark: SedonaContext, blob_client: BlobClient, ingestion_config, dmd_api: DMDApi, iotcore_api: IOTCoreAPI) -> None:
    """
    Execute the upload pipeline for every configured template.
    """
    for template in ingestion_config.templates:
        upload_template(spark, blob_client, template, ingestion_config, dmd_api, iotcore_api)


def main(environment: str) -> None:
    
    configure_logging()

    environment = environment.upper()

    logging.info(f"Starting the upload pipeline for environment '{environment}'...")

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

    spark = create_spark_session(app_name="ingestion-engine-upload")

    try:
        run_upload_pipeline(spark, blob_client, ingestion_config, dmd_api, iotcore_api)
    finally:
        spark.stop()

    logging.info("Upload pipeline completed successfully.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        raise ValueError("Must provide an environment argument.")

    main(environment=sys.argv[1])