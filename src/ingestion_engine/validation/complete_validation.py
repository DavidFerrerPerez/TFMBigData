from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


INVALID_TYPE_FIELDS_COLUMN = "_invalid_type_fields"

REQUIRED_FIELD_MISSING = "required_field_missing"
INVALID_TYPE = "invalid_type"
DUPLICATED_ID = "duplicated_id"
INVALID_GEOMETRY = "invalid_geometry"


def validate_dataframe(df: DataFrame, ingestion_config) -> tuple[DataFrame, DataFrame]:
    config = ingestion_config.data_quality

    _validate_structure(df, config)

    valid_df = df
    rejected_dfs = []

    valid_df, rejected_types = _validate_invalid_types(valid_df)
    if rejected_types is not None:
        rejected_dfs.append(rejected_types)

    valid_df, rejected_nulls = _validate_mandatory_fields(valid_df, config.non_null_fields)
    if rejected_nulls is not None:
        rejected_dfs.append(rejected_nulls)

    valid_df, rejected_duplicates = _validate_duplicated_ids(valid_df, config.id_column)
    rejected_dfs.append(rejected_duplicates)

    valid_df, rejected_geometry = _validate_geometry(valid_df, config.geometry_column)
    rejected_dfs.append(rejected_geometry)

    rejected_df = _combine_rejected_dfs(rejected_dfs)

    if INVALID_TYPE_FIELDS_COLUMN in valid_df.columns:
        valid_df = valid_df.drop(INVALID_TYPE_FIELDS_COLUMN)
        rejected_df = rejected_df.drop(INVALID_TYPE_FIELDS_COLUMN)

    return valid_df, rejected_df


def _validate_structure(df: DataFrame, config) -> None:
    required_columns = set(config.core_fields)
    required_columns.update(config.non_null_fields)
    required_columns.add(config.id_column)
    required_columns.add(config.geometry_column)

    missing_columns = sorted(required_columns - set(df.columns))

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")


def _validate_mandatory_fields(df: DataFrame, non_null_fields: list[str]) -> tuple[DataFrame, DataFrame | None]:
    if not non_null_fields:
        return df, None

    null_conditions = [F.col(column).isNull() for column in non_null_fields]
    null_condition = reduce(lambda left, right: left | right, null_conditions)

    null_fields = F.array_compact(F.array(*[
        F.when(F.col(column).isNull(), F.lit(column))
        for column in non_null_fields
    ]))

    rejected_df = (
        df
        .filter(null_condition)
        .withColumn("_quarantine_error_code", F.lit(REQUIRED_FIELD_MISSING))
        .withColumn("_quarantine_error_message", F.lit("One or more mandatory fields contain null values."))
        .withColumn("_quarantine_field", F.concat_ws(",", null_fields))
    )

    valid_df = df.filter(~null_condition)

    return valid_df, rejected_df


def _validate_duplicated_ids(df: DataFrame, id_column: str) -> tuple[DataFrame, DataFrame]:
    duplicated_ids = (
        df
        .groupBy(id_column)
        .count()
        .filter(F.col("count") > 1)
        .select(id_column)
    )

    rejected_df = (
        df
        .join(duplicated_ids, on=id_column, how="inner")
        .withColumn("_quarantine_error_code", F.lit(DUPLICATED_ID))
        .withColumn("_quarantine_error_message", F.lit("Duplicated ID found."))
        .withColumn("_quarantine_field", F.lit(id_column))
    )

    valid_df = df.join(duplicated_ids, on=id_column, how="left_anti")

    return valid_df, rejected_df


def _validate_geometry(df: DataFrame, geometry_column: str) -> tuple[DataFrame, DataFrame]:
    invalid_condition = F.col(geometry_column).isNotNull() & ~F.expr(f"ST_IsValid(`{geometry_column}`)")

    rejected_df = (
        df
        .filter(invalid_condition)
        .withColumn("_quarantine_error_code", F.lit(INVALID_GEOMETRY))
        .withColumn("_quarantine_error_message", F.lit("Geometry is invalid."))
        .withColumn("_quarantine_field", F.lit(geometry_column))
    )

    valid_df = df.filter(~invalid_condition)

    return valid_df, rejected_df

def _combine_rejected_dfs(rejected_dfs: list[DataFrame]) -> DataFrame:
    rejected_df = rejected_dfs[0]

    for df in rejected_dfs[1:]:
        rejected_df = rejected_df.unionByName(df)

    return rejected_df

def _validate_invalid_types(df: DataFrame) -> tuple[DataFrame, DataFrame | None]:
    if INVALID_TYPE_FIELDS_COLUMN not in df.columns:
        return df, None

    invalid_condition = F.size(F.col(INVALID_TYPE_FIELDS_COLUMN)) > 0

    rejected_df = (
        df
        .filter(invalid_condition)
        .withColumn("_quarantine_error_code", F.lit(INVALID_TYPE))
        .withColumn("_quarantine_error_message", F.lit("One or more fields contain values with an invalid type."))
        .withColumn("_quarantine_field", F.concat_ws(",", F.col(INVALID_TYPE_FIELDS_COLUMN)))
    )

    valid_df = df.filter(~invalid_condition)

    return valid_df, rejected_df