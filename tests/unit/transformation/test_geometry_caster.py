"""Tests for geometry casting functionality in the ingestion engine."""

from unittest.mock import MagicMock, patch

import pytest

from ingestion_engine.transformation.geometry_caster import (
    _normalize_geometry_type,
    cast_geometry,
)


def _configure_mock_functions(mock_F):
    """Configure mocked PySpark functions used by cast_geometry."""
    mock_regexp = MagicMock()
    mock_current_type = MagicMock()
    mock_condition = MagicMock()

    mock_current_type.__eq__.return_value = mock_condition

    mock_F.expr.return_value = MagicMock()
    mock_F.regexp_replace.return_value = mock_regexp
    mock_F.upper.return_value = mock_current_type
    mock_F.col.return_value = MagicMock()

    mock_when = MagicMock()
    mock_F.when.return_value = mock_when
    mock_when.otherwise.return_value = MagicMock()

    return mock_current_type, mock_condition


class TestNormalizeGeometryType:
    """Test suite for geometry type normalization."""

    @pytest.mark.parametrize(
        ("geometry_type", "expected"),
        [
            ("Point", "POINT"),
            ("LineString", "LINESTRING"),
            ("Polygon", "POLYGON"),
            ("MultiPoint", "MULTIPOINT"),
            ("MultiLineString", "MULTILINESTRING"),
            ("MultiPolygon", "MULTIPOLYGON"),
            ("ST_Point", "POINT"),
            ("ST_MultiLineString", "MULTILINESTRING"),
            ("multipoint", "MULTIPOINT"),
            ("st_polygon", "POLYGON"),
        ],
    )
    def test_normalize_geometry_type(self, geometry_type, expected):
        assert _normalize_geometry_type(geometry_type) == expected


class TestCastGeometry:
    """Test suite for cast_geometry function."""

    @pytest.mark.parametrize(
        ("expected_type", "source_type"),
        [
            ("MultiPoint", "POINT"),
            ("MultiLineString", "LINESTRING"),
            ("MultiPolygon", "POLYGON"),
        ],
    )
    def test_cast_single_geometry_to_multi(self, expected_type, source_type):
        df = MagicMock()
        df.columns = ["id", "geometry"]
        df.withColumn.return_value = df

        with patch("ingestion_engine.transformation.geometry_caster.F") as mock_F:
            current_type, condition = _configure_mock_functions(mock_F)

            result = cast_geometry(df, expected_type, "geometry")

            current_type.__eq__.assert_called_once_with(source_type)
            mock_F.when.assert_called_once()
            assert mock_F.when.call_args.args[0] is condition
            df.withColumn.assert_called_once()
            assert result is df

    def test_expected_type_with_st_prefix_is_supported(self):
        df = MagicMock()
        df.columns = ["id", "geometry"]
        df.withColumn.return_value = df

        with patch("ingestion_engine.transformation.geometry_caster.F") as mock_F:
            current_type, _ = _configure_mock_functions(mock_F)

            result = cast_geometry(df, "ST_MultiLineString", "geometry")

            current_type.__eq__.assert_called_once_with("LINESTRING")
            df.withColumn.assert_called_once()
            assert result is df

    def test_expected_type_is_case_insensitive(self):
        df = MagicMock()
        df.columns = ["id", "geometry"]
        df.withColumn.return_value = df

        with patch("ingestion_engine.transformation.geometry_caster.F") as mock_F:
            current_type, _ = _configure_mock_functions(mock_F)

            result = cast_geometry(df, "multilinestring", "geometry")

            current_type.__eq__.assert_called_once_with("LINESTRING")
            df.withColumn.assert_called_once()
            assert result is df

    @pytest.mark.parametrize(
        "expected_type",
        [
            "Point",
            "LineString",
            "Polygon",
            "GeometryCollection",
        ],
    )
    def test_unsupported_cast_returns_unchanged(self, expected_type):
        df = MagicMock()
        df.columns = ["id", "geometry"]

        with patch("ingestion_engine.transformation.geometry_caster.F") as mock_F:
            result = cast_geometry(df, expected_type, "geometry")

            assert result is df
            df.withColumn.assert_not_called()
            mock_F.expr.assert_not_called()

    def test_missing_geometry_column_returns_unchanged(self):
        df = MagicMock()
        df.columns = ["id", "other_col"]

        result = cast_geometry(df, "MultiPoint", "geometry")

        assert result is df
        df.withColumn.assert_not_called()

    def test_empty_expected_type_returns_unchanged(self):
        df = MagicMock()
        df.columns = ["id", "geometry"]

        result = cast_geometry(df, "", "geometry")

        assert result is df
        df.withColumn.assert_not_called()

    def test_none_expected_type_returns_unchanged(self):
        df = MagicMock()
        df.columns = ["id", "geometry"]

        result = cast_geometry(df, None, "geometry")

        assert result is df
        df.withColumn.assert_not_called()

    def test_cast_uses_st_multi_expression(self):
        df = MagicMock()
        df.columns = ["id", "geometry"]
        df.withColumn.return_value = df

        with patch("ingestion_engine.transformation.geometry_caster.F") as mock_F:
            _configure_mock_functions(mock_F)

            cast_geometry(df, "MultiPoint", "geometry")

            expressions = [call.args[0] for call in mock_F.expr.call_args_list]

            assert "ST_Multi(`geometry`)" in expressions

    def test_cast_uses_geometry_type_detection(self):
        df = MagicMock()
        df.columns = ["id", "geometry"]
        df.withColumn.return_value = df

        with patch("ingestion_engine.transformation.geometry_caster.F") as mock_F:
            _configure_mock_functions(mock_F)

            cast_geometry(df, "MultiLineString", "geometry")

            assert mock_F.expr.call_args_list[0].args[0] == (
                "ST_GeometryType(`geometry`)"
            )
            mock_F.regexp_replace.assert_called_once()
            mock_F.upper.assert_called_once()

    def test_cast_uses_custom_geometry_column(self):
        df = MagicMock()
        df.columns = ["id", "geom"]
        df.withColumn.return_value = df

        with patch("ingestion_engine.transformation.geometry_caster.F") as mock_F:
            _configure_mock_functions(mock_F)

            result = cast_geometry(df, "MultiPolygon", "geom")

            expressions = [call.args[0] for call in mock_F.expr.call_args_list]

            assert expressions[0] == "ST_GeometryType(`geom`)"
            assert "ST_Multi(`geom`)" in expressions
            assert df.withColumn.call_args.args[0] == "geom"
            assert result is df

    def test_cast_preserves_dataframe_structure(self):
        df = MagicMock()
        df.columns = ["id", "name", "geometry", "timestamp"]
        df.withColumn.return_value = df

        with patch("ingestion_engine.transformation.geometry_caster.F") as mock_F:
            _configure_mock_functions(mock_F)

            result = cast_geometry(df, "MultiPoint", "geometry")

            assert result is df
            assert result.columns == ["id", "name", "geometry", "timestamp"]