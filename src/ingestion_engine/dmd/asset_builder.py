from typing import Any
from shapely import force_2d
from shapely.geometry import mapping
from ingestion_engine.configuration.models import IngestionConfig
from ingestion_engine.validation.null_validation import is_valid


def build_asset(asset_data, characteristics: list[dict], template_data: dict, ingestion_config: IngestionConfig) -> dict:
    """
    Build the payload required to create an asset in DMD.

    Args:
        asset_data: Spark Row containing the standard asset data.
        characteristics: Characteristics populated for the current asset.
        template_data: Metadata associated with the DMD template.
        ingestion_config: The ingestion configuration containing DMD-related settings.

    Returns:
        dict: DMD asset payload.
    """
    name = f"{ingestion_config.dmd.asset_name_prefix}{str(asset_data['name'])}"

    xv_hash_code = _get_characteristic_value(characteristics, "XV_hash_code")

    code_reference_value = xv_hash_code if is_valid(xv_hash_code) else str(asset_data["id"])
    code_reference = f"{ingestion_config.dmd.code_reference_prefix}{code_reference_value}"

    return {
        "templateId": int(template_data["id"]),
        "templateCode": template_data["code"],
        "characteristics": characteristics,
        "name": name,
        "isEnabled": not bool(template_data["is_deleted"]),
        "isDeleted": bool(template_data["is_deleted"]),
        "originId": ingestion_config.dmd.origin_id,
        "geometry": build_geometry(asset_data, ingestion_config.data_quality.geometry_column),
        "externalObjects": [
            {
                "externalId": asset_data["id"],
                "consumerapplicationId": ingestion_config.dmd.consumer_application_id,
            }
        ],
        "mainHierarchyParent": ingestion_config.dmd.main_hierarchy_parent,
        "codeReference": code_reference,
    }


def _get_characteristic_value(characteristics: list[dict], characteristic_code: str) -> Any:
    """
    Return the value associated with a characteristic code.
    """
    for characteristic in characteristics:
        if characteristic.get("code") == characteristic_code:
            return characteristic.get("value")

    return None


def build_geometry(asset_data, geometry_column: str) -> dict | None:
    """
    Build the GeoJSON-like geometry object expected by DMD.

    Args:
        asset_data: Spark Row containing asset data.
        geometry_column: Name of the column containing the geometry data.

    Returns:
        dict | None: Geometry object or None when the asset has no valid geometry.
    """

    asset_fields = asset_data.asDict(recursive=False)

    if geometry_column not in asset_fields:
        return None

    geom = asset_data[geometry_column]
    if not is_valid(geom):
        return None

    geometry = mapping(force_2d(geom))
    return {"type": geometry["type"], "coordinates": geometry["coordinates"]}