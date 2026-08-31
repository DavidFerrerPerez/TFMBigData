from typing import Any
from shapely import force_2d
from ingestion_engine.validation.null_validation import is_valid


def build_asset(asset_data, characteristics: list[dict], template_data: dict, main_hierarchy_parent: int, geometry_column: str) -> dict:
    """
    Build the payload required to create an asset in DMD.

    Args:
        asset_data: Spark Row containing the standard asset data.
        characteristics: Characteristics populated for the current asset.
        template_data: Metadata associated with the DMD template.
        main_hierarchy_parent: ID of the hierarchy parent where the asset will be created.

    Returns:
        dict: DMD asset payload.
    """
    name = "TFMDFP - " + str(asset_data["name"])

    xv_hash_code = _get_characteristic_value(characteristics, "XV_hash_code")

    return {
        "templateId": int(template_data["id"]),
        "templateCode": template_data["code"],
        "characteristics": characteristics,
        "name": name,
        "isEnabled": not bool(template_data["is_deleted"]),
        "isDeleted": bool(template_data["is_deleted"]),
        "geometry": build_geometry(template_data, asset_data, geometry_column),
        "origin": 1,
        "externalObjects": [
            {
                "externalId": asset_data["id"],
                "consumerapplicationId": 1,
            }
        ],
        "mainHierarchyParent": main_hierarchy_parent,
        "bimFileUrl": "bim_file_url",
        "codeReference": "TFMDFP - " + (xv_hash_code if xv_hash_code is not None else name.replace(" ", "")),
    }


def _get_characteristic_value(characteristics: list[dict], characteristic_code: str) -> Any:
    """
    Return the value associated with a characteristic code.
    """
    for characteristic in characteristics:
        if characteristic.get("code") == characteristic_code:
            return characteristic.get("value")

    return None


def build_geometry(template_data: dict, asset_data, geometry_column: str) -> dict | None:
    """
    Build the GeoJSON-like geometry object expected by DMD.

    Args:
        template_data: DMD template metadata.
        asset_data: Spark Row containing asset data.

    Returns:
        dict | None: Geometry object or None when the asset has no valid geometry.
    """

    asset_fields = asset_data.asDict(recursive=False)

    geometry_type = template_data.get("geometry_type")

    if not is_valid(geometry_type):

        geometry_type = asset_data[geometry_column].geom_type

        if not is_valid(geometry_type):
            return None

    if geometry_column not in asset_fields:
        return None

    coordinates = list(asset_data[geometry_column].coords)

    if not is_valid(coordinates):
        return None

    return {
        "type": geometry_type,
        "coordinates": coordinates,
    }