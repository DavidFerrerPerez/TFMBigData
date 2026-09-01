from functools import reduce

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def validate_dataframe(df: DataFrame, ingestion_config) -> tuple[DataFrame, DataFrame]:
    """
    Validate a transformed DataFrame before writing it.

    Structural validation errors raise an exception.
    Record-level validation errors are returned in the rejected DataFrame.

    Args:
        df (DataFrame): DataFrame to validate.
        ingestion_config: Ingestion configuration containing data quality settings.

    Returns:
        tuple[DataFrame, DataFrame]: Valid and rejected DataFrames.
    """
    data_quality_config = ingestion_config.data_quality

    # 1. Structural validation
    missing_columns = [column for column in data_quality_config.core_fields if column not in df.columns]

    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    valid_df = df
    rejected_dfs = []

    # 2. Mandatory null values
    null_conditions = [F.col(column).isNull() for column in data_quality_config.non_null_fields]

    if null_conditions:
        null_condition = reduce(lambda left, right: left | right, null_conditions)

        null_fields = F.array(*[
            F.when(F.col(column).isNull(), F.lit(column))
            for column in data_quality_config.non_null_fields
        ])

        rejected_nulls = (
            valid_df
            .filter(null_condition)
            .withColumn("_quarantine_error_code", F.lit("required_field_missing"))
            .withColumn("_quarantine_error_message", F.lit("One or more mandatory fields contain null values."))
            .withColumn("_quarantine_field", F.concat_ws(",", null_fields))
        )

        rejected_dfs.append(rejected_nulls)
        valid_df = valid_df.filter(~null_condition)

    # 3. Duplicated IDs
    duplicated_ids = (
        valid_df
        .groupBy(data_quality_config.id_column)
        .count()
        .filter(F.col("count") > 1)
        .select(data_quality_config.id_column)
    )

    rejected_duplicates = (
        valid_df
        .join(duplicated_ids, on=data_quality_config.id_column, how="inner")
        .withColumn("_quarantine_error_code", F.lit("duplicated_id"))
        .withColumn("_quarantine_error_message", F.lit("Duplicated ID found."))
        .withColumn("_quarantine_field", F.lit(data_quality_config.id_column))
    )

    rejected_dfs.append(rejected_duplicates)

    valid_df = valid_df.join(
        duplicated_ids,
        on=data_quality_config.id_column,
        how="left_anti",
    )

    # 4. Geometry validity
    geometry_column = data_quality_config.geometry_column
    invalid_geometry_condition = ~F.expr(f"ST_IsValid(`{geometry_column}`)")

    rejected_geometry = (
        valid_df
        .filter(invalid_geometry_condition)
        .withColumn("_quarantine_error_code", F.lit("invalid_geometry"))
        .withColumn("_quarantine_error_message", F.lit("Geometry is invalid."))
        .withColumn("_quarantine_field", F.lit(geometry_column))
    )

    rejected_dfs.append(rejected_geometry)
    valid_df = valid_df.filter(~invalid_geometry_condition)

    # 5. Combine rejected records
    rejected_df = rejected_dfs[0]

    for rejected in rejected_dfs[1:]:
        rejected_df = rejected_df.unionByName(rejected)

    return valid_df, rejected_df