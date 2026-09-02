import json

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T


INVALID_TYPE_FIELDS_COLUMN = "_invalid_type_fields"


def spark_type_from_template(type_name: str):
    types = {
        "string": T.StringType(),
        "maindata": T.StringType(),
        "iotsignal": T.StringType(),
        "date": T.TimestampType(),
        "double": T.DoubleType(),
        "integer": T.IntegerType(),
        "boolean": T.BooleanType(),
    }

    normalized = (type_name or "").lower()
    if normalized not in types:
        raise ValueError(f"Unsupported DMD characteristic type: {type_name}")

    return types[normalized]


def cast_expr(col_expr, type_name: str):
    """Cast a column expression to the target Spark type."""
    return col_expr.cast(spark_type_from_template(type_name))


def default_literal(default_value, type_name: str):
    """Build a typed Spark literal for a configured default value."""
    target_type = spark_type_from_template(type_name)

    if default_value is None:
        return F.lit(None).cast(target_type)

    t = (type_name or "").lower()

    if t == "date":
        return F.to_timestamp(F.lit(str(default_value)))

    if t == "double":
        return F.lit(default_value).cast(T.DoubleType())

    if t == "integer":
        return F.lit(default_value).cast(T.IntegerType())

    if t == "boolean":
        if isinstance(default_value, bool):
            return F.lit(default_value)

        value = str(default_value).strip().lower()

        if value in {"true", "1", "yes", "y"}:
            return F.lit(True)
        if value in {"false", "0", "no", "n"}:
            return F.lit(False)

        raise ValueError(f"Invalid boolean default value: {default_value}")

    return F.lit(str(default_value)).cast(T.StringType())


def normalize_empty_to_null(col_expr):
    """Convert empty or whitespace-only source values to NULL."""
    return F.when(
        col_expr.isNull() | (F.trim(col_expr.cast(T.StringType())) == ""),
        F.lit(None),
    ).otherwise(col_expr)


def transform_with_template_schema(df: DataFrame, core_fields: list[str], template_schema: list[dict], characteristics_mapping: dict) -> DataFrame:
    """
    Transform the input DataFrame according to the template schema.

    Missing or null source values receive the configured default.
    Non-null source values that cannot be cast are kept as NULL and their
    target fields are recorded in `_invalid_type_fields`.
    """
    

    select_exprs = []
    invalid_type_exprs = []

    for char in template_schema:
        char_code = char.get("code")
        char_type = char.get("type")

        if not char_code:
            raise ValueError(f"Template characteristic without code: {char}")

        map_characteristics = characteristics_mapping.get(char_code, {})

        if not map_characteristics:
            select_exprs.append(F.lit(None).cast(spark_type_from_template(char_type)).alias(char_code))
            invalid_type_exprs.append(F.lit(None).cast(T.StringType()))
            continue

        old_col = map_characteristics.get("field")
        default_val = map_characteristics.get("default_value")

        if old_col not in df.columns:
            select_exprs.append(default_literal(default_val, char_type).alias(char_code))
            invalid_type_exprs.append(F.lit(None).cast(T.StringType()))
            continue

        source_expr = normalize_empty_to_null(F.col(old_col))
        casted_expr = cast_expr(source_expr, char_type)

        invalid_cast = source_expr.isNotNull() & casted_expr.isNull()

        value_expr = F.when(
            source_expr.isNull(),
            default_literal(default_val, char_type),
        ).otherwise(casted_expr)

        select_exprs.append(value_expr.alias(char_code))
        invalid_type_exprs.append(F.when(invalid_cast, F.lit(char_code)))

    for core_field in core_fields:
        if core_field not in df.columns:
            df = df.withColumn(core_field, F.lit(None).cast(T.StringType()))

    invalid_type_fields = F.array_compact(F.array(*invalid_type_exprs)).alias(INVALID_TYPE_FIELDS_COLUMN)

    return df.select(*core_fields, *select_exprs, invalid_type_fields)