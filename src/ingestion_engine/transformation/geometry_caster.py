from pyspark.sql import DataFrame
from pyspark.sql import functions as F


_SINGLE_TO_MULTI = {
    "POINT": "MULTIPOINT",
    "LINESTRING": "MULTILINESTRING",
    "POLYGON": "MULTIPOLYGON",
}

_MULTI_TO_SINGLE = {
    multi: single
    for single, multi in _SINGLE_TO_MULTI.items()
}


def _normalize_geometry_type(geometry_type: str) -> str:
    """
    Normalize a geometry type for comparison.

    Examples:
        Point -> POINT
        ST_LineString -> LINESTRING
        MultiPolygon -> MULTIPOLYGON
    """
    return geometry_type.upper().removeprefix("ST_")


def cast_geometry(df: DataFrame, expected_type: str, geometry_column: str = "geometry") -> DataFrame:
    """
    Cast single-part geometries to their multi-part equivalent when required
    by the expected geometry type.

    Supported conversions:
        Point      -> MultiPoint
        LineString -> MultiLineString
        Polygon    -> MultiPolygon

    Geometries that already have the expected type, are null, or cannot be
    safely converted are left unchanged.

    Args:
        df: Spark DataFrame containing the geometry column.
        expected_type: Geometry type expected by the target template.
        geometry_column: Name of the geometry column.

    Returns:
        DataFrame with compatible single-part geometries converted to
        multi-part geometries.
    """
    if geometry_column not in df.columns or not expected_type:
        return df

    expected_type = _normalize_geometry_type(expected_type)

    source_type = _MULTI_TO_SINGLE.get(expected_type)

    if source_type is None:
        return df

    current_type = F.upper(
        F.regexp_replace(
            F.expr(f"ST_GeometryType(`{geometry_column}`)"),
            "^ST_",
            "",
        )
    )

    return df.withColumn(
        geometry_column,
        F.when(
            current_type == source_type,
            F.expr(f"ST_Multi(`{geometry_column}`)"),
        ).otherwise(F.col(geometry_column)),
    )