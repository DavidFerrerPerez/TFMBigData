import os
import logging
import json
from shutil import copy
import sys
import math

from sedona.spark import SedonaContext

from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.configuration.loader import load_ingestion_config
from ingestion_engine.storage.geoparquet_reader import read_geoparquet_to_df
from ingestion_engine.dmd.dmd_api import DMDApi
from ingestion_engine.iotcore.iotcore_api import IOTCoreAPI
from ingestion_engine.logging.config import configure_logging
from ingestion_engine.spark.session import create_spark_session
from ingestion_engine.configuration.validation import validate_blob_config


def create_characteristics_list(template_characteristics: dict) -> list:
    """
    Create a list of characteristics from the template characteristics dictionary to be used for uploading.

    Args:
        template_characteristics (dict): A dictionary containing template characteristics.

    Returns:
        list: A list of characteristics extracted from the template characteristics dictionary.
    """

    characteristics = []

    for index in template_characteristics:
        item = {
            "name": str.replace(str.replace(index.get("name"), " ", "_"), "_-_", "_"),
            "value": set_default_value(index.get("type")),                 
            "code": index.get("code"),    
            "type": index.get("type")
        }
        
        # Since the logic is yet to be implemented, right now we just skip this fields
        if item.get("type") in ["iotsynoptic", "iotsinoptic"]:
            pass
        else:
            characteristics.append(item)

    return characteristics

def set_default_value(type: str):
    """
    Set a default value based on the provided type.
    """
    if type == "double":
        return 0.0
    elif type == "integer":
        return 0
    elif type in ["maindata", "date"]:
        return None
    else:
        return ""


def update_characteristics(template_characteristics_list: list, row, dmdApi: DMDApi, iotcoreapi: IOTCoreAPI) -> list:
    char_dict = {item['code']: item for item in template_characteristics_list}

    TYPE_HANDLERS = {
        "double":      lambda col: str(row[col] if _is_valid(row[col]) else 0.0),
        "integer":     lambda col: str(int(row[col] if _is_valid(row[col]) else 0)),
        "iotsignal":   lambda col: add_iot_signals(asset_id=str(row["externalId"]), iotcoreapi=iotcoreapi),
        "maindata":    lambda col: get_maindata_value_id(row[col], col, dmdApi),
        "date":        lambda col: (row[col].isoformat() + 'T00:00:00') if _is_valid(row[col]) else None,
    }

    for col, char in ((c, char_dict[c]) for c in row.keys() if c in char_dict):
        handler = TYPE_HANDLERS.get(char["type"])
        value = handler(col) if handler else row[col]
        if char["type"] != "maindata" or value is not None:
            char["value"] = value

    return list(char_dict.values())


def _is_valid(value) -> bool:
        if value is None:
            return False
        try:
            return not math.isnan(value)
        except TypeError:
            return True


def _find_maindata_id(maindata_dict: dict, maindata_value: str) -> int:
    """
    Find the ID of a maindata value in a maindata dictionary.

    Args:
        maindata_dict (dict): A dictionary containing maindata values and their corresponding IDs.
        maindata_value (str): The maindata value to find the ID for.

    Returns:
        int or None: The ID of the maindata value if found, otherwise None.
    """
    for item in maindata_dict.get("relations", []):
        if str(item.get("name")) == str(maindata_value):
            return item.get("id")
    return None


def get_maindata_value_id(maindata_value: str, maindata_relation_master: str, dmdApi: DMDApi) -> float:
    """
    Get the ID of a maindata value for a given maindata relation master using the DMD API.
    
    Args:
        maindata_value (str): The maindata value to find the ID for.
        maindata_relation_master (str): The name of the maindata relation master.
        dmdApi (DMDApi): An instance of the DMDApi class to interact with the DMD API.

    Returns:
        float or None: The ID of the maindata value if found, otherwise None.
    """

    logging.debug(f"Getting maindata value for relation master: {maindata_relation_master} and value: {maindata_value}")

    if maindata_value == "Unknown" or maindata_value is None:
        return None

    maindata = dmdApi.get_maindata_values_by_code(maindata_relation_master)

    maindata_id = _find_maindata_id(maindata, maindata_value)

    logging.debug(f"Found maindata value '{maindata_value}' with ID: {maindata_id} in '{maindata_relation_master}'")

    return maindata_id

def add_iot_signals(asset_id: str, iotcoreapi: IOTCoreAPI) -> List[Dict[str, Any]]:
    try:

        signals: List[Dict[str, Any]] = []

        uids = iotcoreapi.get_uids_from_tag_name(asset_id)

        for uid in uids:

            signals.append(
                {
                    "uid": uid,
                    "type": "SIGNAL",
                    "name": asset_id,
                }
            )

        return signals

    except AttributeError:
        return []
    except Exception:
        return []

def build_asset(asset_data, characteristics: list, row_template_data, main_hierarchy_parent: int) -> dict:

    xv_hash_code = None

    for char in characteristics:
        if char.get("code") == "XV_hash_code":
            xv_hash_code = char.get("value")

    name = str(asset_data["name"])
    
    asset = {
        "templateId": int(row_template_data["id"]),
        "templateCode": row_template_data["code"],
        "characteristics": characteristics,
        "name": name,
        "isEnabled": bool(not row_template_data["is_deleted"]),
        "isDeleted": bool(row_template_data["is_deleted"]),
        "geometry": adapt_geometry(row_template_data, asset_data),
        "origin": 1,
        "externalObjects": [
            {
                "externalId": asset_data["id"],
                "consumerapplicationId": 1
            }
        ],
        "mainHierarchyParent": main_hierarchy_parent,
        "bimFileUrl": 'bim_file_url',
        "codeReference": xv_hash_code if xv_hash_code is not None else name.replace(" ", "")
    }
    
    return asset

def adapt_geometry(row_template_data, asset_data) -> dict:
    if "geometry_type" not in row_template_data or not _is_valid(row_template_data["geometry_type"]):
        return None
    
    if "coordinates" not in asset_data or not _is_valid(asset_data["coordinates"]):
        return None

    geometry_type = row_template_data["geometry_type"]
    coordinates = asset_data["coordinates"]

    geometry = {"type": geometry_type, "coordinates": coordinates}

    return geometry

def upload_asset_to_dmd(asset_list: list, template: str, dmdApi: DMDApi) -> dict:
    """
    Uploads an asset to the DMD API.

    Args:
        asset_list (list): The list of asset data to be uploaded.
        template (str): The name of the template being uploaded.
        dmdApi (DMDApi): An instance of the DMDApi class to interact with the DMD API.

    Returns:
        dict: The response from the DMD API after attempting to upload the asset.
    """
    try:
        response = dmdApi.create_assets(asset_list)
        if "error" in str(response).lower() and "Duplicate Name Exception" not in str(response):
                    logging.warning(f"Error detected in response for batch. Writing asset names to {template}_failed_assets.txt")
                    with open(f"{template}_failed_assets.txt", "a") as f:
                        for asset in asset_list:
                            f.write(asset.get('name', 'unknown') + ": " + str(response) + "\n")
        asset_list.clear()
    except Exception as e:
        logging.error(f"Error uploading asset {asset.get('name')} to DMD: {e}")
        return {"error": str(e)}


def run_upload_pipeline(spark: SedonaContext, blob_client: BlobClient, ingestion_config: dict, dmdapi: DMDApi, iotcoreapi: IOTCoreAPI) -> None:

    for template in ingestion_config.templates:
        logging.info(f"Uploading table {template}...")

        try:
            df_assets = read_geoparquet_to_df(spark, blob_client, f"{ingestion_config.storage.paths.standard}/{template}.parquet")

        except Exception as e:
            logging.error(f"Error reading table {template} from blob storage: {e}")
            continue

        template_metadata = dmdapi.get_template_metadata(template)
        template_schema = dmdapi.get_template_schema_by_id(template_metadata.get("id"))

        template_characteristics_list = create_characteristics_list(template_schema)

        asset_list = []

        for row in df_assets.collect():

            row_specific_characteristics = update_characteristics(template_characteristics_list, row, dmdapi, iotcoreapi)

            asset = build_asset(row, row_specific_characteristics, template_schema, ingestion_config.main_hierarchy_parent)

            asset_list.append(copy.deepcopy(asset))

            if len(asset_list) >= ingestion_config.batch_size:
                upload_asset_to_dmd(asset_list, template, dmdapi)
                

        if asset_list:
            upload_asset_to_dmd(asset_list, template, dmdapi)

        logging.info(f"Table {template} uploaded successfully.")

def main(environment: str):

    ingestion_config = load_ingestion_config("config/ingestion.yaml")

    if environment not in ingestion_config.available_environments:
        raise ValueError(f"Invalid environment '{environment}'. Available environments: {ingestion_config.available_environments}")

    logging.info("Starting the upload pipeline...")

    configure_logging()

    dmdapi = DMDApi(
        dmd_api_url=os.environ[f'DMD_API_URL_{environment}'],
        token=os.environ[f'DMD_API_TOKEN_{environment}']
    )

    spark = create_spark_session(app_name="ingestion-engine-upload")

    connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING")
    container_name = ingestion_config.storage.container

    validate_blob_config(connection_string, container_name)

    dmdapi = DMDApi(
        dmd_api_url=os.environ[f'DMD_API_URL_{environment}'],
        token=os.environ[f'DMD_API_TOKEN_{environment}']
    )

    iotcoreapi = IOTCoreAPI(
        iotcore_api_url=os.environ[f'IOTCORE_API_URL_{environment}'],
        token=os.environ[f'IOTCORE_API_TOKEN_{environment}'],
        driver=os.environ.get(f'IOTCORE_API_DRIVER_{environment}')
    )

    blob_client = BlobClient(
        connection_string=connection_string,
        container_name=container_name,
    )

    run_upload_pipeline(spark, blob_client, ingestion_config, dmdapi, iotcoreapi)

    spark.stop()

    logging.info("Upload pipeline completed successfully.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) < 2:
        raise Exception("Must provide an environment argument.")

    main(environment=sys.argv[1].upper())