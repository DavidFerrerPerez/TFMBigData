from unittest.mock import MagicMock

from ingestion_engine.transformation.table_unificator import unify_tables


def test_unify_single_table_returns_it():
    df = MagicMock()
    result = unify_tables(MagicMock(), [df])
    assert result is df


def test_unify_two_tables_calls_union_by_name():
    df1 = MagicMock()
    df2 = MagicMock()
    union_result = MagicMock()
    df1.unionByName.return_value = union_result

    result = unify_tables(MagicMock(), [df1, df2])

    df1.unionByName.assert_called_once_with(df2)
    assert result is union_result


def test_unify_three_tables_chains_unions():
    df1 = MagicMock()
    df2 = MagicMock()
    df3 = MagicMock()
    union12 = MagicMock()
    union123 = MagicMock()
    df1.unionByName.return_value = union12
    union12.unionByName.return_value = union123

    result = unify_tables(MagicMock(), [df1, df2, df3])

    df1.unionByName.assert_called_once_with(df2)
    union12.unionByName.assert_called_once_with(df3)
    assert result is union123


def test_unify_spark_session_is_not_used():
    """spark parameter is accepted but not actually used."""
    df = MagicMock()
    spark = MagicMock()
    unify_tables(spark, [df])
    spark.assert_not_called()
