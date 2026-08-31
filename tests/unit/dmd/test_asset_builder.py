from unittest.mock import MagicMock

from ingestion_engine.dmd.asset_builder import build_asset, build_geometry


def _make_asset_data(name="Pump Station 1", asset_id="asset-001", geometry=None, geometry_column="geometry"):
    data = {"name": name, "id": asset_id, geometry_column: geometry}
    mock = MagicMock()
    mock.__getitem__ = MagicMock(side_effect=lambda key: data[key])
    mock.asDict.return_value = {k: v for k, v in data.items() if v is not None}
    return mock


def _make_template(template_id=42, code="PUMP", is_deleted=False, geometry_type="Point"):
    return {
        "id": template_id,
        "code": code,
        "is_deleted": is_deleted,
        "geometry_type": geometry_type,
    }


def _make_geometry(geom_type="Point", coords=None):
    geometry = MagicMock()
    geometry.geom_type = geom_type
    geometry.coords = coords if coords is not None else [(1.0, 2.0)]
    return geometry


# build_asset — name and code reference

def test_build_asset_name_is_prefixed_with_tfmdfp():
    asset_data = _make_asset_data(name="Station 1")
    result = build_asset(asset_data, [], _make_template(), main_hierarchy_parent=10, geometry_column="geometry")
    assert result["name"] == "TFMDFP - Station 1"


def test_build_asset_uses_xv_hash_code_as_code_reference():
    asset_data = _make_asset_data(name="Station 1")
    characteristics = [{"code": "XV_hash_code", "value": "HASH123"}]
    result = build_asset(asset_data, characteristics, _make_template(), main_hierarchy_parent=10, geometry_column="geometry")
    assert result["codeReference"] == "TFMDFP - HASH123"


def test_build_asset_falls_back_to_name_when_no_hash_code():
    asset_data = _make_asset_data(name="Station 1")
    result = build_asset(asset_data, [], _make_template(), main_hierarchy_parent=10, geometry_column="geometry")
    # name has no spaces when used as fallback
    assert "TFMDFP-Station1" in result["codeReference"]


# build_asset — template fields

def test_build_asset_is_enabled_when_template_is_not_deleted():
    asset_data = _make_asset_data()
    result = build_asset(asset_data, [], _make_template(is_deleted=False), main_hierarchy_parent=1, geometry_column="geometry")
    assert result["isEnabled"] is True
    assert result["isDeleted"] is False


def test_build_asset_is_disabled_when_template_is_deleted():
    asset_data = _make_asset_data()
    result = build_asset(asset_data, [], _make_template(is_deleted=True), main_hierarchy_parent=1, geometry_column="geometry")
    assert result["isEnabled"] is False
    assert result["isDeleted"] is True


def test_build_asset_sets_correct_template_id_and_code():
    asset_data = _make_asset_data()
    result = build_asset(asset_data, [], _make_template(template_id=99, code="VALVE"), main_hierarchy_parent=1, geometry_column="geometry")
    assert result["templateId"] == 99
    assert result["templateCode"] == "VALVE"


def test_build_asset_sets_external_object_with_asset_id():
    asset_data = _make_asset_data(asset_id="ext-42")
    result = build_asset(asset_data, [], _make_template(), main_hierarchy_parent=1, geometry_column="geometry")
    assert result["externalObjects"][0]["externalId"] == "ext-42"


def test_build_asset_sets_main_hierarchy_parent():
    asset_data = _make_asset_data()
    result = build_asset(asset_data, [], _make_template(), main_hierarchy_parent=7, geometry_column="geometry")
    assert result["mainHierarchyParent"] == 7


# build_geometry

def test_build_geometry_returns_type_and_coordinates_from_template():
    geometry = _make_geometry(coords=[(10.0, 20.0)])
    asset_data = _make_asset_data(geometry=geometry)
    asset_data.asDict.return_value = {"geometry": geometry}

    result = build_geometry({"geometry_type": "Point"}, asset_data, "geometry")

    assert result == {"type": "Point", "coordinates": [(10.0, 20.0)]}


def test_build_geometry_falls_back_to_asset_geom_type_when_template_has_none():
    geometry = _make_geometry(geom_type="LineString", coords=[(0.0, 0.0), (1.0, 1.0)])
    asset_data = _make_asset_data(geometry=geometry)
    asset_data.asDict.return_value = {"geometry": geometry}

    result = build_geometry({"geometry_type": None}, asset_data, "geometry")

    assert result["type"] == "LineString"
    assert result["coordinates"] == [(0.0, 0.0), (1.0, 1.0)]


def test_build_geometry_returns_none_when_no_geometry_type_at_all():
    geometry = _make_geometry(geom_type=None)
    asset_data = _make_asset_data(geometry=geometry)
    asset_data.asDict.return_value = {"geometry": geometry}

    result = build_geometry({"geometry_type": None}, asset_data, "geometry")

    assert result is None


def test_build_geometry_returns_none_when_geometry_column_is_absent_from_row():
    asset_data = MagicMock()
    asset_data.asDict.return_value = {}  # geometry column not present

    result = build_geometry({"geometry_type": "Point"}, asset_data, "geometry")

    assert result is None
