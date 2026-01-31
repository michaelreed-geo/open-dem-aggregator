"""
DEM datasets for onshore England hosted on the Defra Survey Data Portal
https://environment.data.gov.uk/survey
"""

import json
from datetime import datetime
from http import HTTPMethod
from typing import List
from xml.etree import ElementTree

from odemagg.datasets import DemCollection, DemTile
from odemagg.vector import PolygonWKT
from odemagg.web import https_request


def _format_collection(meta: dict) -> DemCollection:
    """
    Converts a metadata dictionary into a `DemCollection` object.

    This function extracts relevant fields from a metadata dictionary—typically one that includes a
    metadata URL and collection identifier—and returns a structured `DemCollection` dataclass
    instance.

    Args:
        meta (dict): A dictionary containing metadata for a DEM collection.
            Must include at least the keys `'id'` and `'metadata_url'`.

    Returns:
        DemCollection: A structured object representing the DEM collection metadata.
    """
    xml_namespaces = {
        "csw": "http://www.opengis.net/cat/csw/2.0.2",
        "gco": "http://www.isotc211.org/2005/gco",
        "gmd": "http://www.isotc211.org/2005/gmd",
        "gml": "http://www.opengis.net/gml/3.2",
    }

    product_id = meta["metadata_url"].split("/")[-1]
    root = ElementTree.fromstring(
        https_request(
            url="https://environment.data.gov.uk/discover/ea/csw?"
            f"request=GetRecordById&id={product_id}",
        )
    )

    # look for attribution statement
    attribution = ""
    abstract = root.find(".//gmd:abstract/gco:CharacterString", xml_namespaces).text
    if abstract.find("Attribution statement: ") != -1:
        attribution = abstract[abstract.find("Attribution statement: ") + 23 :]
    else:
        attribution = ""

    # get file format
    i = root.find(".//gmd:MD_Format/gmd:name/gco:CharacterString", xml_namespaces).text
    data_format = i[i.find("(") + 1 : -1]

    # get crs
    i = root.find(
        ".//gmd:RS_Identifier/gmd:code/gco:CharacterString", xml_namespaces
    ).text
    crs = "EPSG:" + i.split("/")[-1]

    # get start and end dates
    date_end = datetime.strptime(
        root.find(".//gml:TimePeriod/gml:endPosition", xml_namespaces).text, "%Y-%m-%d"
    )
    date_start = datetime.strptime(
        root.find(".//gml:TimePeriod/gml:beginPosition", xml_namespaces).text,
        "%Y-%m-%d",
    )

    # get dem type (dsm or dtm)
    if "dsm" in meta["id"]:
        dem_type = "dsm"
    elif "dtm" in meta["id"]:
        dem_type = "dtm"
    else:
        dem_type = None

    collection = DemCollection(
        abstract=abstract,
        attribution=attribution,
        contact=root.find(
            ".//gmd:electronicMailAddress/gco:CharacterString", xml_namespaces
        ).text,
        crs=crs,
        date_end=date_end,
        date_start=date_start,
        dem_type=dem_type,
        details=root.find(".//gmd:statement/gco:CharacterString", xml_namespaces).text,
        format=data_format,
        host=root.find(
            ".//gmd:organisationName/gco:CharacterString", xml_namespaces
        ).text,
        id=meta["id"],
        licence=root.find(
            ".//gmd:useLimitation/gco:CharacterString", xml_namespaces
        ).text,
        metadata_url=meta["metadata_url"],
        title=root.find(".//gmd:title/gco:CharacterString", xml_namespaces).text,
        use_constraints=root.find(
            ".//gmd:otherConstraints/gco:CharacterString", xml_namespaces
        ).text,
    )
    return collection


def get_collections(ids: List[str] | None = None) -> List[DemCollection]:
    """
    Retrieves a list of available DEM collections from the Defra Data Services Platform.

    This function queries the Defra portal and returns a list of `DemCollection` instances
    representing each available collection, including associated metadata such as title, CRS, date
    range, and access URLs.

    Args:
        ids(List[DemCollection], optional): A list of collection ids to return.
            If not provided, returns all.

    Returns:
        List[DemCollection]: A list of DEM collections available from the Defra portal.
    """
    metas = [
        {
            "id": "lidar_composite_dtm-1m",
            "metadata_url": "https://environment.data.gov.uk/dataset/13787b9a-26a4-4775-8523-806d13af58fc",
        },
        {
            "id": "lidar_composite_dtm-2m",
            "metadata_url": "https://environment.data.gov.uk/dataset/09ea3b37-df3a-4e8b-ac69-fb0842227b04",
        },
        {
            "id": "lidar_composite_first_return_dsm-1m",
            "metadata_url": "https://environment.data.gov.uk/dataset/df4e3ec3-315e-48aa-aaaf-b5ae74d7b2bb",
        },
        {
            "id": "lidar_composite_first_return_dsm-2m",
            "metadata_url": "https://environment.data.gov.uk/dataset/df4e3ec3-315e-48aa-aaaf-b5ae74d7b2bb",
        },
        {
            "id": "lidar_composite_last_return_dsm-1m",
            "metadata_url": "https://environment.data.gov.uk/dataset/9ba4d5ac-d596-445a-9056-dae3ddec0178",
        },
        {
            "id": "lidar_composite_last_return_dsm-2m",
            "metadata_url": "https://environment.data.gov.uk/dataset/f083c5dc-504f-4428-9811-a1b2519fa279",
        },
        {
            "id": "lidar_point_cloud",
            "metadata_url": "https://environment.data.gov.uk/dataset/094d4ec8-4c21-4aa6-817f-b7e45843c5e0",
        },
        {
            "id": "lidar_tiles_dtm",
            "metadata_url": "https://environment.data.gov.uk/dataset/dbadf364-0192-4bcf-a223-f3d403f08682",
        },
        {
            "id": "lidar_tiles_dsm",
            "metadata_url": "https://environment.data.gov.uk/dataset/1021ecff-6549-4dbe-b8a0-48ae72a3c698",
        },
    ]
    if not ids:
        _metas = metas
    else:
        _metas = [i for i in metas if i["id"] in ids]

    collections = []
    for i in _metas:
        collections.append(_format_collection(i))
    return collections


def _format_tile(data: dict, collections: List[DemCollection] | None = None) -> DemTile:
    """
    Converts a tile metadata dictionary from the Defra survey API into a `DemTile` object.

    This function extracts and parses relevant fields from a raw tile dictionary returned by the
    Defra survey search endpoint, and constructs a structured `DemTile` instance. Optionally, a list
     of preloaded `DemCollection` objects can be passed to improve lookup performance.

    Args:
        data (dict): A dictionary representing a DEM tile, typically returned from:
            https://environment.data.gov.uk/backend/catalog/api/tiles/collections/survey/search
        collections (List[DemCollection], optional): A list of `DemCollection` instances.
            If provided, the function will match the tile's collection ID against this list instead
            of querying all known collections. Defaults to None.

    Returns:
        DemTile: A `DemTile` instance representing the tile metadata.
    """
    # form the collection id based on the dataset product and resolution
    collection_id = f"{data['product']['id']}"
    if float(data["resolution"]["id"]) > 0 and "tiles" not in collection_id:
        # if time stamped tiles, don't include resolution
        collection_id += f"-{data['resolution']['label']}"

    if not collections:
        collections = get_collections()

    file_type = None
    collection = None
    if len(collections) > 0:
        try:
            collection = [i for i in collections if i.id == collection_id][0]
            match collection.format:
                case "GeoTIFF":
                    file_type = ".tif"
                case "LAZ":
                    file_type = ".laz"
                case _:
                    file_type = None
        except IndexError:
            pass

    tile = DemTile(
        collection=collection,
        date=datetime.strptime(data["year"]["label"], "%Y"),
        geometry=None,  # TODO: transform grid reference into polygon
        resolution=data["resolution"]["label"],
        size=0,
        title=data["label"],
        type=file_type,
        url=f"{data['uri']}?subscription-key=public",
        headers={"Ocp-Apim-Subscription-Key": "public"},
    )
    return tile


def get_data_intersecting_geometry(
    geometry: PolygonWKT, collections: list[str] | None = None
) -> List[DemTile]:
    """
    Retrieves DEM tiles from one or more collections that intersect a given polygon geometry.

    This function queries the Defra Data Services Platform and returns a list of `DemTile` objects
    representing data tiles that spatially intersect the input geometry. Optionally, you can limit
    the query to a specific subset of collections.

    Args:
        geometry (PolygonWKT): A PolygonWKT object to use for spatial intersection.
        collections (list[str], optional): A list of DEM collection IDs to filter the query.
            If not provided, all known collections will be queried.

    Returns:
        List[DemTile]: A list of `DemTile` instances that intersect the specified geometry.
    """
    payload = {
        "coordinates": [[list(i) for i in geometry.transform("EPSG:4326").coordinates]],
        "type": "Polygon",
    }

    data = json.loads(
        https_request(
            "https://environment.data.gov.uk/backend/catalog/api/tiles/collections/survey/search",
            method=HTTPMethod.POST,
            body=payload,
            headers={"Content-Type": "application/geo+json"},
        )
    )["results"]

    tiles = None
    _collections = get_collections(
        collections
    )  # get metadata for target collections (or all if not specified)
    if data:
        tiles = [_format_tile(i, _collections) for i in data]
        # drop tiles without a collection (i.e. unsupported datasets)
        tiles = [i for i in tiles if i.collection]
    return tiles
