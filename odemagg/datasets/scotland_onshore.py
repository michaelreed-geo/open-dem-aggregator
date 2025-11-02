"""
DEM datasets for onshore Scotland hosted on the Scottish Remote Sensing Portal
https://remotesensingdata.gov.scot/
"""

import json
from datetime import datetime
from http import HTTPMethod
from pathlib import Path
from typing import List

from odemagg.datasets import DemCollection, DemTile
from odemagg.vector import PolygonWKT
from odemagg.web import https_request


def _format_collection(data: dict) -> DemCollection:
    """
    Transforms a collection dictionary returned by the catalog request into a DemCollection
    instance.

    Args:
        data (dict): Dictionary representing a collection result returned by
            https://srsp-catalog.jncc.gov.uk/search/collection/scotland-gov/*

    Returns:
        DemCollection: A DemCollection object representing the collection metadata.
    """
    # flexible approach to handle datetime in two formats
    try:
        date_end = datetime.strptime(
            data["metadata"]["temporalExtent"]["end"], "%Y-%m-%dT%H:%M:%SZ"
        )
        date_start = datetime.strptime(
            data["metadata"]["temporalExtent"]["begin"], "%Y-%m-%dT%H:%M:%SZ"
        )
    except ValueError:
        try:
            date_end = datetime.strptime(
                data["metadata"]["temporalExtent"]["end"], "%Y-%m-%d"
            )
            date_start = datetime.strptime(
                data["metadata"]["temporalExtent"]["begin"], "%Y-%m-%d"
            )
        except ValueError as exc:
            raise ValueError(
                f"Unsupported datetime format: {data['metadata']['temporalExtent']['begin']}"
            ) from exc

    collection = DemCollection(
        abstract=data["metadata"]["abstract"],
        attribution=data["metadata"]["useConstraints"],
        contact=data["metadata"]["responsibleOrganisation"]["email"],
        crs=data["metadata"]["spatialReferenceSystem"],
        date_end=date_end,
        date_start=date_start,
        details="",
        format=data["metadata"]["dataFormat"],
        host="Scottish Government",
        id=data["name"],
        licence="",
        metadata_url=data["metadata"]["additionalInformationSource"],
        title=data["metadata"]["title"],
        use_constraints=data["metadata"]["useConstraints"],
    )
    return collection


def get_collections() -> list[DemCollection]:
    """
    Retrieves a list of valid DEM collections from the Scottish Remote Sensing Portal.

    Returns:
        list[DemCollection]: A list of DemCollection instances representing available DEM
            collections.
    """
    catalog_json = json.loads(
        https_request(
            url="https://srsp-catalog.jncc.gov.uk/search/collection/scotland-gov/*"
        )
    )
    collections = []
    for i in catalog_json["result"]:
        # only collect datasets - ignore services
        if i["metadata"]["resourceType"] == "dataset":
            collections.append(_format_collection(i))
    collections = sorted(collections, key=lambda i: i.date_end)
    return collections


def _format_tile(data: dict, collections: List[DemCollection] | None = None) -> DemTile:
    """
    Transforms a tile dictionary returned by the product query into a DemTile instance.

    Args:
        data (dict): Dictionary representing a single tile result returned by
            https://srsp-catalog.jncc.gov.uk/search/product.
        collections (List[DemCollection] | None): Optional list of DEM collections. If provided, the
            function will search only within these collections to match the tile's collection ID.
            If None, all collections will be considered (slower).

    Returns:
        DemTile: A DemTile object representing the tile metadata.
    """
    if not collections:
        collections = get_collections()

    if len(collections) > 0:
        collection = [i for i in collections if i.id == data["collectionName"]][0]

    # construct valid WKT geometry
    geometry = "POLYGON (("
    for i in data["footprint"]["coordinates"][0][0]:
        geometry += f"{i[0]} {i[1]}, "
    geometry = geometry[:-2] + "))"

    tile = DemTile(
        collection=collection,
        date=collection.date_end,
        geometry=PolygonWKT(
            geometry=geometry, crs="EPSG:4326"
        ),  # all SRSP use 4326 as CRS
        resolution="",  # TODO: implement
        size=data["data"]["product"]["http"]["size"],
        title=data["data"]["product"]["title"],
        type=Path(data["data"]["product"]["http"]["url"]).suffix,
        url=data["data"]["product"]["http"]["url"],
    )
    return tile


def get_data_intersecting_geometry(
    geometry: PolygonWKT,
    collections: list[str] | None = None,
    limit: int = 9999,
    offset: int = 0,
) -> list[DemTile]:
    """
    Identifies DEM tiles that intersect with the provided geometry.

    Args:
        geometry (PolygonWKT): A polygon geometry (in WKT format) to search for intersecting tiles.
        collections (list[str] | None): Optional list of collection IDs to filter the search.
            If None, all available collections are queried.
        limit (int): Maximum number of results to return. Constrained by the SRSP API
            (default is 9999).
        offset (int): API offset parameter, included for pagination but purpose may be undefined.

    Returns:
        list[DemTile]: A list of DemTile instances representing data that intersects the given
            geometry.
    """
    # transform CRS to 4326 - mandatory for SRSP API
    geometry.transform("EPSG:4326", replace=True)
    all_collections = None
    if collections is None:
        # use all collections
        all_collections = get_collections()  # store for later use
        collections = [i.id for i in all_collections]
    payload = {
        "collections": collections,
        "footprint": geometry.geometry,
        "limit": limit,
        "offset": offset,
        "spatialop": "intersects",
    }
    data = json.loads(
        https_request(
            url="https://srsp-catalog.jncc.gov.uk/search/product",
            method=HTTPMethod.POST,
            body=payload,
            headers={"Content-Type": "application/json"},
        )
    )["result"]
    if all_collections is None:
        # initialise if it doesn't already exist
        all_collections = get_collections()
    # format data into DemTiles
    results = [_format_tile(i, all_collections) for i in data]
    return results
