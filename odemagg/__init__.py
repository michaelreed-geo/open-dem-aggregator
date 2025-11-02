"""
Module with primary methods for downloading, clipping and merging DEM datasets.
"""

import tempfile
from pathlib import Path
from typing import List, Literal

from odemagg.datasets import DemTile, england_onshore, scotland_onshore, wales_onshore
from odemagg.raster import create_mosaic
from odemagg.utils import run_with_timer, unzip_files
from odemagg.vector import PolygonWKT
from odemagg.web import https_download_parallel


def search(
    geometry: PolygonWKT,
    region: Literal["england_onshore", "scotland_onshore", "wales_onshore"],
    collections: List[str] | None = None,
) -> list[DemTile] | None:
    """

    Args:
        geometry:
        region:

    Returns:

    """
    result = None
    match region:
        case "england_onshore":
            result = england_onshore.get_data_intersecting_geometry(
                geometry=geometry, collections=collections
            )
        case "scotland_onshore":
            result = scotland_onshore.get_data_intersecting_geometry(
                geometry=geometry, collections=collections
            )
        case "wales_onshore":
            result = wales_onshore.get_data_intersecting_geometry(
                geometry=geometry, collections=collections
            )
    return result


def download(geometry: PolygonWKT, tiles: list[DemTile], file_path: Path) -> Path:
    """
    Downloads DEM tiles intersecting a given geometry, merges them, and saves to disc.

    This function downloads the specified DEM tiles, optionally clips them to the given geometry,
    merges them into a single raster, and writes the output to the provided file path.
    Temporary files can be cleaned up after processing.

    Args:
        geometry (PolygonWKT): PolygonWKT object to which the DEM data will be clipped.
        tiles (list[DemTile]): List of DEM tiles to download and merge.
        file_path (Path): Path where the merged DEM raster will be saved.

    Returns:
        Path: The path to the final merged DEM raster file.
    """
    with tempfile.TemporaryDirectory() as temp:
        temp_dir = Path(temp)
        raw_rasters = https_download_parallel(
            urls=[i.url for i in tiles],
            headers=[i.headers for i in tiles],
            output_dir=temp_dir,
        )
        all_files = raw_rasters  # track all files downloaded for future cleanup

        # unzip files if necessary
        remove_indices = []  # track which files to remove
        for i, tile in enumerate(tiles):
            if raw_rasters[i].suffix == ".zip":
                remove_indices.append(i)
                unzipped_files = unzip_files(
                    zip_path=raw_rasters[i], target_dir=temp_dir, file_types=[tile.type]
                )
                for j in unzipped_files:
                    raw_rasters.append(j)
                    all_files.append(j)
        if remove_indices:
            # remove the .zip files from raw_rasters
            temp = [
                item for i, item in enumerate(raw_rasters) if i not in remove_indices
            ]
            raw_rasters = temp
        # transform geometry to match target CRS
        geometry = geometry.transform(out_crs=tiles[0].collection.crs, replace=True)
        mosaic = create_mosaic(
            rasters=raw_rasters,
            geometry=geometry,
            file_path=file_path,
            crs=geometry.crs,
        )
        # TODO: provide option to preserve cache temporarily
        return mosaic


# if __name__ == "__main__":
    # wales_search = run_with_timer(
    #     search,
    #     PolygonWKT(
    #         geometry="Polygon ((300361 211260, 301482 210446, 302131 209788, 300483 209739, 300202 210484, 300361 211260))",
    #         crs="epsg:27700",
    #     ),
    #     "wales_onshore",
    #     ["nrw_lidar_tile_catalogue_archive_dtm"],
    # )
    # wales_search = [
    #     i for i in wales_search if i.resolution == "2m" and i.date.year == 2004
    # ]
    #
    # wales_mosaic = run_with_timer(
    #     download,
    #     PolygonWKT(
    #         geometry="Polygon ((300361 211260, 301482 210446, 302131 209788, 300483 209739, 300202 210484, 300361 211260))",
    #         crs="epsg:27700",
    #     ),
    #     wales_search,
    #     Path(r"C:\Users\Michael\Downloads\mosaic_wales.tif"),
    # )

    # scotland_search = run_with_timer(
    #     search,
    #     PolygonWKT(
    #         geometry="Polygon ((258139 661706, 258631 661718, 258592 661110, 257816 661214, 258139 661706))",
    #         crs="epsg:27700",
    #     ),
    #     "scotland_onshore",
    #     ["scotland-gov/lidar/phase-5/dsm"],
    # )
    #
    # scotland_mosaic = run_with_timer(
    #     download,
    #     PolygonWKT(
    #         geometry="Polygon ((258139 661706, 258631 661718, 258592 661110, 257816 661214, 258139 661706))",
    #         crs="epsg:27700",
    #     ),
    #     scotland_search,
    #     Path(r"C:\Users\Michael\Downloads\mosaic_scotland.tif"),
    # )
    #
    #
    # england_search = run_with_timer(
    #     search,
    #     PolygonWKT(
    #         geometry="Polygon ((340185 556115, 340677 556128, 340638 555520, 339861 555623, 340185 556115))",
    #         crs="epsg:27700",
    #     ),
    #     "england_onshore",
    #     ["lidar_composite_dtm-1m"],
    # )
    #
    #
    # england_mosaic = run_with_timer(
    #     download,
    #     PolygonWKT(
    #         geometry="Polygon ((340185 556115, 340677 556128, 340638 555520, 339861 555623, 340185 556115))",
    #         crs=CRS("epsg:27700"),
    #     ),
    #     england_search,
    #     Path(r"C:\Users\Michael\Downloads\mosaic_england.tif"),
    # )
