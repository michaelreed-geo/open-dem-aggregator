"""
Tests for the odemagg.vectors module.
"""

import pytest
from pyproj.crs import CRS

from odemagg.vector import PolygonWKT, get_bounds, transform_polygon, wkt_is_polygon


### odemagg.vector.wkt_is_polygon
def test_wkt_is_polygon_type():
    geometry = None
    with pytest.raises(ValueError):
        wkt_is_polygon(geometry)


def test_wkt_is_polygon_startswith():
    geometry = "LINESTRING (0 0, 0 10, 10 10, 10 0)"
    with pytest.raises(ValueError):
        wkt_is_polygon(geometry)


def test_wkt_is_polygon_starts_bracket():
    geometry = "POLYGON (0 0, 0 10, 10 10, 10 0, 0 0))"
    with pytest.raises(ValueError):
        wkt_is_polygon(geometry)


def test_wkt_is_polygon_ends_bracket():
    geometry = "POLYGON ((0 0, 0 10, 10 10, 10 0, 0 0)"
    with pytest.raises(ValueError):
        wkt_is_polygon(geometry)


def test_wkt_is_polygon_coord_pairs():
    geometry = "POLYGON ((0 0, 0 10, 10 10, 10 0 3, 0 0))"
    with pytest.raises(ValueError):
        wkt_is_polygon(geometry)


def test_wkt_is_polygon_non_numeric():
    geometry = "POLYGON ((0 0, 0 10a, 10 10, 10 0, 0 0))"
    with pytest.raises(ValueError):
        wkt_is_polygon(geometry)


def test_wkt_is_polygon_closed():
    # check first and last coordinate pairs are identical
    geometry = "POLYGON ((0 5, 0 10, 10 10, 10 0, 0 0))"
    with pytest.raises(ValueError):
        wkt_is_polygon(geometry)


def test_wkt_is_polygon_valid():
    geometry = "POLYGON ((0 0, 0 10, 10 10, 10 0, 0 0))"
    expected = True
    assert wkt_is_polygon(geometry) == expected


### odemagg.vector.get_bounds
def test_get_bounds_invalid_wkt():
    geometry = "POlYGON ((0 0, 0 10 0, 10 10, 10 0, 0 0))"
    with pytest.raises(ValueError):
        get_bounds(geometry)


def test_get_bounds_simple():
    geometry = "POlYGON ((0 0, 0 10, 10 10, 10 0, 0 0))"
    expected = (0.0, 0.0, 10.0, 10.0)
    assert get_bounds(geometry) == expected


def test_get_bounds_negative():
    geometry = "POlYGON ((-10 -10, -10 0, 0 0, 0 -10, -10 -10))"
    expected = (-10.0, -10.0, 0.0, 0.0)
    assert get_bounds(geometry) == expected


def test_get_bounds_accuracy():
    geometry = "POlYGON ((0.123 0.123, 0.123 10.987, 10.987 10.987, 10.987 0.123, 0.123 0.123))"
    accuracy = 2
    expected = (0.12, 0.12, 10.99, 10.99)
    assert get_bounds(geometry, accuracy) == expected


### odemagg.vector.transform_polygon
def test_transform_polygon_27700_to_3857():
    geometry = "POlYGON ((0 0, 0 10, 10 10, 10 0, 0 0))"
    in_crs = "EPSG:27700"
    out_crs = "EPSG:3857"
    accuracy = 5
    expected = (
        "POLYGON ((-841259.18155 6405988.47735,-841260.32437 6406003.90565,-841244.93931 6406005.05168,"
        "-841243.79652 6405989.62337,-841259.18155 6405988.47735))"
    )
    assert transform_polygon(geometry, in_crs, out_crs, accuracy) == expected


def test_transform_polygon_27700_to_4326():
    geometry = "POlYGON ((0 0, 0 10, 10 10, 10 0, 0 0))"
    in_crs = "EPSG:27700"
    out_crs = "EPSG:4326"
    accuracy = 5
    expected = "POLYGON ((-7.55716 49.76681,-7.55717 49.76690,-7.55703 49.76690,-7.55702 49.76681,-7.55716 49.76681))"
    assert transform_polygon(geometry, in_crs, out_crs, accuracy) == expected


### PolygonWKT
def test_PolygonWKT_bounds():
    polygon = PolygonWKT(
        geometry="POlYGON ((0 0, 0 10, 10 10, 10 0, 0 0))", crs="EPSG:27700"
    )
    expected = (0.0, 0.0, 10.0, 10.0)
    assert polygon.bounds == expected


def test_PolygonWKT_coordinates():
    polygon = PolygonWKT(
        geometry="POlYGON ((0 0, 0 10, 10 10, 10 0, 0 0))", crs="EPSG:27700"
    )
    expected = [(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0), (0.0, 0.0)]
    assert polygon.coordinates == expected


def test_PolygonWKT_transform_27700_to_3857():
    polygon = PolygonWKT(
        geometry="POlYGON ((0 0, 0 10, 10 10, 10 0, 0 0))", crs="EPSG:27700"
    )
    out_crs = "EPSG:3857"
    accuracy = 5
    transformed = polygon.transform(out_crs, accuracy)
    expected_geometry = (
        "POLYGON ((-841259.18155 6405988.47735,-841260.32437 6406003.90565,-841244.93931 6406005.05168,"
        "-841243.79652 6405989.62337,-841259.18155 6405988.47735))"
    )
    expected_crs = CRS(out_crs)
    assert transformed.geometry == expected_geometry
    assert transformed.crs == expected_crs


def test_PolygonWKT_transform_27700_to_3857_replace():
    polygon = PolygonWKT(
        geometry="POlYGON ((0 0, 0 10, 10 10, 10 0, 0 0))", crs="EPSG:27700"
    )
    out_crs = "EPSG:3857"
    accuracy = 5
    polygon.transform(out_crs, accuracy, replace=True)
    expected_geometry = (
        "POLYGON ((-841259.18155 6405988.47735,-841260.32437 6406003.90565,"
        "-841244.93931 6406005.05168,-841243.79652 6405989.62337,-841259.18155 6405988.47735))"
    )
    expected_crs = CRS(out_crs)
    assert polygon.geometry == expected_geometry
    assert polygon.crs == expected_crs


def test_PolygonWKT_from_coordinates():
    expected_coordinates = [(0, 0), (0, 10), (10, 10), (10, 0), (0, 0)]
    expected_crs = CRS("EPSG:27700")
    polygon = PolygonWKT.from_coordinates(
        coordinates=expected_coordinates, crs=expected_crs
    )
    assert polygon.coordinates == expected_coordinates
    assert polygon.crs == expected_crs
