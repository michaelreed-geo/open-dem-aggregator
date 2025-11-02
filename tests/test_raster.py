from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import pytest
import rasterio
import rasterio.windows

from odemagg.raster import clip_raster, round_window
from odemagg.vector import PolygonWKT


def test_round_window():
    window = rasterio.windows.Window(0.1, 0.3, 99.7, 99.5)
    rounded = round_window(window)
    expected = rasterio.windows.Window(0.0, 0.0, 100.0, 100.0)
    assert rounded == expected


@pytest.fixture
def temp_raster_all_data():
    """Creates a temporary single-band raster for testing."""
    data = [[0, 1, 2, 3], [1, 2, 3, 0], [2, 3, 0, 1], [3, 0, 1, 2]]
    dtype = np.uint8
    x, y = 0, 4
    x_size, y_size = 1, 1

    data = np.array(data, dtype=dtype)
    transform = rasterio.transform.from_origin(
        west=x, north=y, xsize=x_size, ysize=y_size
    )

    with NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        with rasterio.open(
            tmp.name,
            "w",
            driver="GTiff",
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs="EPSG:4326",
            transform=transform,
            nodata=0,
        ) as dst:
            dst.write(data, 1)
        yield Path(tmp.name)


def test_clip_raster(temp_raster_all_data):
    polygon = PolygonWKT(
        geometry="POlYGON ((1 1, 1 3, 3 3, 3 1, 1 1))", crs="EPSG:27700"
    )

    result = clip_raster(temp_raster_all_data, polygon)

    assert isinstance(result, rasterio.io.MemoryFile)
    with result.open() as src:
        clipped = src.read(1)
        assert clipped.shape == (2, 2)
        assert src.count == 1
        assert np.array_equal(clipped[:2, :2], np.array([[2, 3], [3, 0]]))


def test_clip_raster_outside_bounds(temp_raster_all_data):
    polygon = PolygonWKT(
        geometry="POlYGON ((10 10, 10 20, 20 20, 20 10, 10 10))", crs="EPSG:27700"
    )

    result = clip_raster(temp_raster_all_data, polygon)
    assert result is None


@pytest.fixture
def temp_raster_nodata():
    """Creates a temporary single-band including some nodata values raster for testing."""
    data = [[0, 1, 2, 3], [1, -1, -1, 0], [2, 3, 0, 1], [3, 0, 1, 2]]
    dtype = np.float64
    x, y = 0, 4
    x_size, y_size = 1, 1

    data = np.array(data, dtype=dtype)
    transform = rasterio.transform.from_origin(
        west=x, north=y, xsize=x_size, ysize=y_size
    )

    with NamedTemporaryFile(suffix=".tif", delete=False) as tmp:
        with rasterio.open(
            tmp.name,
            "w",
            driver="GTiff",
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=data.dtype,
            crs="EPSG:4326",
            transform=transform,
            nodata=-1,
        ) as dst:
            dst.write(data, 1)
        yield Path(tmp.name)


def test_clip_raster_no_data(temp_raster_nodata):
    polygon = PolygonWKT(
        geometry="POlYGON ((1 1, 1 3, 3 3, 3 1, 1 1))", crs="EPSG:27700"
    )

    result = clip_raster(temp_raster_nodata, polygon)

    assert isinstance(result, rasterio.io.MemoryFile)
    with result.open() as src:
        clipped = src.read(1)
        assert clipped.shape == (1, 2)
        assert src.count == 1
        assert np.array_equal(clipped[:1, :2], np.array([[3, 0]]))


# TODO: test_create_mosaic
# TODO: test_write_raster_to_disc
