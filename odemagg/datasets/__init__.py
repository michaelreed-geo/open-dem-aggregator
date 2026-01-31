"""
Module containing classes for interacting with data and metadata of DEM datasets.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from odemagg.vector import PolygonWKT


@dataclass
class DemCollection:
    """
    Represents metadata for a collection of Digital Elevation Model (DEM) data.

    This class stores standardized metadata describing a DEM dataset collection, including spatial
    reference, licensing, temporal coverage, and access details.

    Attributes:
        abstract (str): A brief description of the DEM dataset collection.
        attribution (str): Credit or source to whom the dataset should be attributed.
        contact (str): Contact information for dataset-related inquiries.
        crs (str): Coordinate Reference System of the DEM data as an EPSG string.
        date_end (datetime): End date of the temporal coverage for the dataset.
        date_start (datetime): Start date of the temporal coverage for the dataset.
        details (str): Additional notes or detailed description about the dataset.
        format (str): Format of the DEM files (e.g. "GeoTIFF", "LAZ").
        host (str): Organisation who hosts the dataset.
        id (str): Unique identifier for the DEM dataset collection used within this library.
        licence (str): License under which the data is distributed (e.g. "Open Government Licence").
        metadata_url (str): URL pointing to the full metadata for the dataset.
        title (str): Human-readable title of the dataset.
        use_constraints (str): Description of any constraints on use, distribution, or modification.
    """

    abstract: str
    attribution: str
    contact: str
    crs: str
    date_end: datetime | None
    date_start: datetime | None
    dem_type: Literal["dsm", "dtm"] | None
    details: str
    format: str
    host: str
    id: str
    licence: str
    metadata_url: str
    title: str
    use_constraints: str
    # TODO: add type pointer for DSM and DTM


@dataclass
class DemTile:
    """
    Represents metadata for an individual tile of a Digital Elevation Model (DEM) dataset.

    This class links a single DEM tile to its parent collection and stores tile-specific metadata
    such as spatial coverage, acquisition date, resolution, and access URL.

    Attributes:
        collection (DemCollection): The parent DEM collection this tile belongs to.
        date (datetime): Acquisition or publication date of the DEM tile, as provided by host
            metadata.
        geometry (PolygonWKT): Geometry and CRS of the tile footprint as a PolygonWKT object.
        resolution (str): Spatial resolution of the tile (e.g. "1m").
        size (int): File size of the tile in bytes.
        title (str): Human-readable title or name of the tile.
        type (str): File type or data format (e.g., ".tif", ".laz").
        url (str): Direct download URL for accessing the tile.
        headers (dict, optional): Optional headers required for accessing the URL.
    """

    collection: DemCollection
    date: datetime
    geometry: PolygonWKT
    resolution: str
    size: int  # in bytes
    title: str
    type: str
    url: str
    headers: dict = field(default_factory=dict)  # defaults to empty
