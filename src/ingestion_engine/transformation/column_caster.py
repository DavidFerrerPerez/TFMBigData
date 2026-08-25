import json

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql import types as T

def spark_type_from_template(type_name: str):
    t = (type_name or "").lower()
    if t == "string":
        return T.StringType()
    if t == "date":
        return T.TimestampType()
    if t == "double":
        return T.DoubleType()
    if t == "integer":
        return T.IntegerType()
    if t == "boolean":
        return T.BooleanType()

    return T.StringType()


def cast_expr(col_expr, type_name: str):
    """Cast a column expression to target Spark type."""
    target_type = spark_type_from_template(type_name)
    return col_expr.cast(target_type)


def default_literal(default_value, type_name: str):
    """
    Build a typed Spark literal for defaults.
    Returns a Column expression.
    """
    if default_value is None:
        return F.lit(None).cast(spark_type_from_template(type_name))

    t = (type_name or "").lower()

    if t == "date":
        return F.to_timestamp(F.lit(str(default_value)))

    if t == "double":
        return F.lit(default_value).cast(T.DoubleType())

    if t == "integer":
        return F.lit(default_value).cast(T.IntegerType())

    if t == "boolean":
        if isinstance(default_value, bool):
            return F.lit(default_value).cast(T.BooleanType())
        s = str(default_value).strip().lower()
        if s in {"true", "1", "yes", "y"}:
            return F.lit(True)
        if s in {"false", "0", "no", "n"}:
            return F.lit(False)
        return F.lit(None).cast(T.BooleanType())

    return F.lit(str(default_value)).cast(T.StringType())


def normalize_empty_to_null(col_expr, type_name: str):
    """
    Equivalent of pandas replace('', NA), only meaningful for strings.
    For non-string, returns input unchanged.
    """
    t = (type_name or "").lower()
    if t in {"string", "maindata", ""}:
        return F.when(F.trim(col_expr) == "", F.lit(None)).otherwise(col_expr)
    return col_expr


def transform_with_template_schema(
    df: DataFrame,
    core_fields: list[str],
    template_schema: list[dict]
) -> DataFrame:
    """

    Transforms the input DataFrame `df` based on the provided `template_schema` and `core_fields`.

    Args:
        df (DataFrame): The input DataFrame to be transformed.
        core_fields (list[str]): A list of core field names that should be preserved in the transformed DataFrame.
        template_schema (list[dict]): A list of dictionaries representing the template schema. Each dictionary should contain at least the keys "code" and "type".
            [
                {
                    'id': 1874,
                    'name': 'Xylem Vue - Decommission date',
                    'value': '<Date>',
                    'code': 'XV_decommission_date',
                    'type': 'date',
                    'format': '2022-10-05T17:56:49.469'
                },
            ]
    
    Returns:
        DataFrame: A new DataFrame with columns transformed according to the template schema and characteristics mapping.
    """

    with open("config/mappings/characteristics_mapping.json", "r", encoding="utf-8") as f:
        characteristics_mapping = json.load(f)

    select_exprs = []


    for char in template_schema:
        char_code = char.get("code")
        char_type = char.get("type")
        map_characteristics = characteristics_mapping.get(char_code, {})

        if map_characteristics:
            old_col = map_characteristics.get("field")
            default_val = map_characteristics.get("default_value", None)

            if old_col in df.columns:
                expr = F.col(old_col)
                expr = cast_expr(expr, char_type)
            else:
                expr = F.lit(None).cast(spark_type_from_template(char_type))

            expr = normalize_empty_to_null(expr, char_type)
            expr = F.coalesce(expr, default_literal(default_val, char_type))
        else:
            expr = F.lit(None).cast(spark_type_from_template(char_type))

        select_exprs.append(expr.alias(char_code))

    for core_field in core_fields:
        if core_field not in df.columns:
            df = df.withColumn(core_field, F.lit(None).cast(T.StringType()))

    df_new_clean = df.select(*core_fields, *select_exprs)
    return df_new_clean