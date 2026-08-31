import logging
from typing import Any

from ingestion_engine.dmd.dmd_api import DMDApi
from ingestion_engine.iotcore.iotcore_api import IOTCoreAPI
from ingestion_engine.validation.null_validation import is_valid


def create_characteristics_list(template_characteristics: list[dict]) -> list[dict]:
    """
    Create the base list of DMD characteristics for a template.

    Args:
        template_characteristics: Characteristics returned by the DMD template schema.

    Returns:
        list[dict]: Base characteristic definitions with their default values.
    """
    characteristics = []

    for characteristic in template_characteristics:
        item = {
            "name": _normalize_characteristic_name(characteristic.get("name")),
            "code": characteristic.get("code"),
            "type": characteristic.get("type"),
        }

        # IoT synoptic characteristics are currently not supported.
        if item["type"] in {"iotsynoptic", "iotsinoptic"}:
            continue

        characteristics.append(item)

    return characteristics


def _normalize_characteristic_name(name: str | None) -> str:
    """
    Normalize a DMD characteristic name.
    """
    if name is None:
        return ""

    return str(name).replace(" ", "_").replace("_-_", "_")


def set_default_value(characteristic_type: str | None) -> Any:
    """
    Return the default value for a DMD characteristic type.

    Args:
        characteristic_type: DMD characteristic type.

    Returns:
        Default value for the provided characteristic type.
    """
    if characteristic_type == "double":
        return 0.0

    if characteristic_type == "integer":
        return 0

    if characteristic_type in {"maindata", "date"}:
        return None

    return ""


def build_characteristics(template_characteristics: list[dict], row, dmd_api: DMDApi, iotcore_api: IOTCoreAPI) -> list[dict]:
    """
    Build the characteristics for a specific asset.

    Args:
        template_characteristics (list[dict]): Characteristic definitions of the DMD template.
        row: Spark Row containing the asset data.
        dmd_api (DMDApi): DMD API client.
        iotcore_api (IOTCoreAPI): IoT Core API client.

    Returns:
        list[dict]: Characteristics populated with the values of the asset.
    """
    row_dict = row.asDict()
    characteristics = []

    for characteristic in template_characteristics:
        code = characteristic["code"]
        characteristic_type = characteristic["type"]
        value = set_default_value(characteristic_type)

        if characteristic_type == "iotsignal":
            value = add_iot_signals(str(row_dict["externalId"]), iotcore_api)
        elif code in row_dict:
            value = get_characteristic_value(characteristic_type, row_dict[code], code, dmd_api)

        characteristics.append({
            "name": characteristic["name"],
            "value": value,
            "code": code,
            "type": characteristic_type
        })

    return characteristics


def get_characteristic_value(characteristic_type: str, value: Any, code: str, dmd_api: DMDApi) -> Any:
    """
    Convert a characteristic value according to its DMD type.
    """
    if characteristic_type == "double":
        return _handle_double(value)

    if characteristic_type == "integer":
        return _handle_integer(value)

    if characteristic_type == "maindata":
        return get_maindata_value_id(value, code, dmd_api)

    if characteristic_type == "date":
        return _handle_date(value)

    return value


def _handle_double(value: Any) -> str:
    """
    Convert a value to the format expected by a DMD double characteristic.
    """
    if not is_valid(value):
        return "0.0"

    return str(value)


def _handle_integer(value: Any) -> str:
    """
    Convert a value to the format expected by a DMD integer characteristic.
    """
    if not is_valid(value):
        return "0"

    return str(int(value))


def _handle_date(value: Any) -> str | None:
    """
    Convert a date to the format expected by DMD.
    """
    if not is_valid(value):
        return None

    return value.isoformat()


def get_maindata_value_id(maindata_value: Any, maindata_relation_master: str, dmd_api: DMDApi) -> int | None:
    """
    Get the DMD ID associated with a maindata value.

    Args:
        maindata_value: Value present in the source data.
        maindata_relation_master: Code of the DMD maindata relation.
        dmd_api: DMD API client.

    Returns:
        int | None: Matching maindata ID, or None when no value is found.
    """
    if maindata_value in {None, "Unknown"}:
        return None

    logging.debug(f"Getting maindata value for relation '{maindata_relation_master}' and value '{maindata_value}'")

    maindata_dict = dmd_api.get_maindata_values_by_code(maindata_relation_master)
    maindata_id = maindata_dict.get(maindata_value, None)

    logging.debug(f"Found maindata value '{maindata_value}' with ID '{maindata_id}' in relation '{maindata_relation_master}'")

    return maindata_id


def add_iot_signals(asset_id: str, iotcore_api: IOTCoreAPI) -> list[dict]:
    """
    Get the IoT signals associated with an asset.

    Args:
        asset_id: External ID used to find the associated IoT signal.
        iotcore_api: IoT Core API client.

    Returns:
        list[dict]: Signal definitions expected by DMD.
    """
    try:
        uids = iotcore_api.get_uids_from_tag_name(asset_id)

        return [
            {
                "uid": uid,
                "type": "SIGNAL",
                "name": asset_id,
            }
            for uid in uids
        ]

    except AttributeError:
        logging.warning(f"No IoT signals found for asset '{asset_id}'")
        return []

    except Exception as e:
        logging.exception(f"Error retrieving IoT signals for asset '{asset_id}': {e}")
        return []