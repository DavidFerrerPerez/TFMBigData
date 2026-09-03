from pyspark.sql import DataFrame
from pyspark.sql import functions as F

_SINGLE_GEOMETRY_TYPES = {"Point", "LineString", "Polygon"}


def cast_geometry(df: DataFrame, expected_type: str, geometry_column: str = "geometry") -> DataFrame:
    """
    Attempt to cast a single-part geometry column to its multi-part equivalent
    (e.g. LineString to MultiLineString) when it matches the expected type.

    Args:
        df: Spark DataFrame containing the geometry column.
        expected_type: Geometry type expected by the DMD template.
        geometry_column: Name of the geometry column to cast.

    Returns:
        The DataFrame with the geometry column cast to the expected multi-part
        type when applicable, or unchanged otherwise.
    """

    if geometry_column not in df.columns or not expected_type:
        return df

    current_type = F.regexp_replace(F.expr(f"ST_GeometryType(`{geometry_column}`)"), "^ST_", "")

    should_cast = current_type.isin(*_SINGLE_GEOMETRY_TYPES) & (
        F.concat(F.lit("Multi"), current_type) == F.lit(expected_type)
    )

    return df.withColumn(
        geometry_column,
        F.when(should_cast, F.expr(f"ST_Multi(`{geometry_column}`)")).otherwise(F.col(geometry_column)),
    )