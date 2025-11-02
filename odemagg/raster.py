"""
Module for handling raster IO and processing.
"""

import math
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import rasterio
import rasterio.merge
from pyproj import CRS

from odemagg.vector import PolygonWKT


def round_window(window: rasterio.windows.Window) -> rasterio.windows.Window:
    """
    Rounds a rasterio window to ensure it aligns fully with the raster resolution.

    Args:
        window (rasterio.windows.Window): The window to be rounded.

    Returns:
        rasterio.windows.Window: The rounded window.
    """
    col_off = math.floor(window.col_off)
    row_off = math.floor(window.row_off)
    width = math.ceil(window.col_off + window.width) - col_off
    height = math.ceil(window.row_off + window.height) - row_off
    return rasterio.windows.Window(col_off, row_off, width, height)


def clip_raster(
    raster: Path,
    geometry: PolygonWKT,
    band: int = 1,
    clip_to_data: bool = True,
    no_data: float | int | None = None,
    file_path: Path | str = "memory",
    compress: str = "LZW",
) -> Path | rasterio.io.MemoryFile:
    """
    Clips a raster to the area of a geometry.

    Args:
        raster (Path): Path to the raster file.
        geometry (PolygonWKT): Geometry to clip to.
        band (int, optional): Raster band of interest. Defaults to 1.
        clip_to_data (bool, optional):
            If True, raster is clipped to only the non-nodata elements within the geometry extent.
            If False, raster is clipped to the geometry extent, potentially including large nodata
            areas. Defaults to True.
        no_data (float or int or None, optional): Value for nodata. Defaults to the raster's current
            nodata value.
        file_path (Path or str, optional):
            If path-like, writes raster to that path.
            If 'memory', writes to a rasterio.io.MemoryFile. Defaults to 'memory'.
        compress (str, optional): Compression type if writing to disc. Defaults to 'LZW'.

    Returns:
        Path or rasterio.io.MemoryFile: The clipped raster dataset or in-memory raster file.
    """
    # TODO: transform geometry to match raster crs
    with rasterio.open(raster) as src:
        geometry_bounds = geometry.bounds
        # check that geometry intersects with raster
        within = True
        if geometry_bounds[2] <= src.bounds[0] or geometry_bounds[0] >= src.bounds[2]:
            within = False
        elif geometry_bounds[3] <= src.bounds[1] or geometry_bounds[1] >= src.bounds[3]:
            within = False

        if not within:
            warnings.warn("Geometry not within raster bounds.")
            return None

        # restrict bounds to extent of raster
        geometry_bounds = (
            max(geometry_bounds[0], src.bounds[0]),
            max(geometry_bounds[1], src.bounds[1]),
            min(geometry_bounds[2], src.bounds[2]),
            min(geometry_bounds[3], src.bounds[3]),
        )

        window = rasterio.windows.from_bounds(*geometry_bounds, src.transform)
        window = round_window(window)
        raster_window = src.read(indexes=band, window=window)
        raster_transform = src.window_transform(window)
        meta = src.meta.copy()

        if clip_to_data:
            # exclude areas of no data from clipping bounds
            if src.nodata is None and no_data is None:
                warnings.warn(
                    "You must specify the nodata value for this raster."
                    "Clipping to full geometry bounds."
                )
            else:
                if no_data is None and src.nodata:
                    no_data = src.nodata
                data_mask = raster_window != no_data
                if not np.any(data_mask):
                    warnings.warn("No non-nodata found within geometry.")
                    return None

                # get bounds of non-nodata within raster_window
                rows, cols = np.where(data_mask)
                row_start, row_stop = rows.min(), rows.max() + 1
                col_start, col_stop = cols.min(), cols.max() + 1

                # create sub-window within raster_window to limit to non-nodata only
                subwindow = rasterio.windows.Window(
                    col_off=col_start,
                    row_off=row_start,
                    width=col_stop - col_start,
                    height=row_stop - row_start,
                )

                # create a composite window of the original and subwindow
                composite_window = rasterio.windows.Window(
                    col_off=window.col_off + subwindow.col_off,
                    row_off=window.row_off + subwindow.row_off,
                    width=subwindow.width,
                    height=subwindow.height,
                )
                raster_window = src.read(indexes=band, window=composite_window)
                raster_transform = src.window_transform(composite_window)
                meta.update({"nodata": no_data})

        meta.update(
            {
                "height": raster_window.shape[0],
                "width": raster_window.shape[1],
                "transform": raster_transform,
            }
        )
        if file_path == "memory":
            raster_output = rasterio.io.MemoryFile()
            with raster_output.open(**meta) as file_dest:
                file_dest.write(raster_window, 1)
        else:
            raster_output = write_raster_to_disc(
                raster_array=raster_window,
                raster_meta=meta,
                file_path=file_path,
                compress=compress,
            )
    return raster_output


def create_mosaic(
    rasters: list[Path],
    geometry: PolygonWKT,
    crs: CRS | str | None = None,
    file_path: Path | str = "memory",
    compress: str = "LZW",
    max_workers: int = 5,
) -> Path | rasterio.io.MemoryFile:
    """
    Creates a clipped and merged mosaic from a list of raster tiles over a target geometry.

    This function reads a set of raster files, clips each to the given geometry, and merges
    them into a single mosaic raster. The resulting mosaic is either written to disc or kept
    in memory.

    Args:
        rasters (list[Path]): List of file paths to individual raster tiles.
        geometry (PolygonWKT): A polygon defining the clipping extent.
        crs (CRS | str | None, optional): Manually specify the CRS of the output raster.
            Defaults to use the existing CRS of the raster (if provided).
        file_path (Path | str, optional): Output file path. If set to 'memory', the result is stored
            in a `rasterio.io.MemoryFile`. Defaults to 'memory'.
        compress (str, optional): Compression algorithm to use if writing to disc. Defaults to LZW.
        max_workers (int, optional): Number of threads to use for parallel clipping. Defaults to 5.

    Returns:
        Path | rasterio.io.MemoryFile: File path of the written mosaic or an in-memory raster file.
    """
    # TODO: geometry and CRS need to match
    clipped_rasters = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(clip_raster, path, geometry) for path in rasters]
        for future in futures:
            if (
                future.result() is not None
            ):  # skip cases where raster has no relevant data
                clipped_rasters.append(future.result().open())

    out_meta = clipped_rasters[0].meta.copy()
    # get nodata value
    nodatas = min({i.nodata for i in clipped_rasters})
    match out_meta["dtype"]:
        case "int16":
            nodata = np.int16(nodatas)
        case "int32":
            nodata = np.int32(nodatas)
        case "uint8":
            nodata = np.uint8(nodatas)
        case "uint16":
            nodata = np.uint16(nodatas)
        case "uint32":
            nodata = np.uint32(nodatas)
        case "float32":
            nodata = np.float32(nodatas)
        case "float64":
            nodata = np.float64(nodatas)

    mosaic, out_transform = rasterio.merge.merge(clipped_rasters, nodata=nodata)

    out_meta.update(
        {
            "height": mosaic.shape[1],
            "width": mosaic.shape[2],
            "transform": out_transform,
            "nodata": nodata,
        }
    )

    if crs:
        if isinstance(crs, str):
            crs = CRS(crs)
        out_meta.update({"crs": rasterio.CRS.from_string(crs.srs)})

    # Clean up in-memory datasets
    for mem in clipped_rasters:
        mem.close()

    if file_path == "memory":
        raster_output = rasterio.io.MemoryFile()
        with raster_output.open(**out_meta) as file_dest:
            file_dest.write(mosaic, 1)
    else:
        raster_output = write_raster_to_disc(
            raster_array=mosaic,
            raster_meta=out_meta,
            file_path=file_path,
            compress=compress,
        )
    return raster_output


def write_raster_to_disc(
    raster_array: np.ndarray,
    raster_meta: dict,
    file_path: Path,
    compress: str = "LZW",
) -> Path:
    """
    Writes a raster array to disc with specified metadata and compression.

    Args:
        raster_array (np.ndarray): The raster data as a NumPy array.
        raster_meta (dict): Metadata dictionary for the raster.
        file_path (Path): Path where the raster file will be saved.
        compress (str, optional): Compression method to use (e.g., 'LZW'). Defaults to 'LZW'.

    Returns:
        Path: The path of the written raster file.
    """
    with rasterio.open(file_path, "w", **raster_meta, compress=compress) as file_dest:
        if raster_array.ndim == 2:
            file_dest.write(raster_array, 1)
        else:
            file_dest.write(raster_array)
    return file_path
