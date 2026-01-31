"""
DEM datasets for onshore Wales hosted on Data Map Wales
https://datamap.gov.wales/maps/lidar-data-download/view#/
"""

from copy import copy
from datetime import datetime
from typing import List
from xml.etree import ElementTree

from odemagg.datasets import DemCollection, DemTile
from odemagg.ows import wfs_intersect_filter
from odemagg.vector import PolygonWKT
from odemagg.web import https_request


def _format_collection(meta: dict) -> DemCollection:
    """
    Converts a metadata dictionary into a `DemCollection` object.

    This function extracts relevant fields from a metadata dictionary—typically one that includes a
    metadata URL and collection identifier—and returns a structured `DemCollection` instance.

    Args:
        meta (dict): A dictionary containing metadata for a DEM collection.
            Must include at least the keys `'id'` and `'metadata_url'`.

    Returns:
        DemCollection: A structured object representing the DEM collection metadata.
    """
    xml_namespaces = {
        "gco": "http://www.isotc211.org/2005/gco",
        "gmd": "http://www.isotc211.org/2005/gmd",
    }

    root = ElementTree.fromstring(
        https_request(
            url=meta["metadata_url"],
        )
    )

    # look for attribution statement
    attribution = ""
    abstract = root.find(".//gmd:abstract/gco:CharacterString", xml_namespaces).text
    if abstract.find("Attribution statement ") != -1:
        attribution = abstract[abstract.find("Attribution statement ") + 22 :]
    else:
        attribution = ""

    # get file format
    data_format = ""
    if meta["id"].startswith("welsh_government_lidar_tile_catalogue_2020_2023"):
        data_format = (
            "GeoTIFF"  # manual override - hosted data are Indexes which point to .shp
        )
    elif meta["id"].startswith("nrw_lidar_tile_catalogue_archive"):
        data_format = "ASCII"
    # i = root.find(".//gmd:MD_Format/gmd:name/gco:CharacterString", xml_namespaces).text
    # data_format = i[i.find("(") + 1 : -1]

    # get crs
    crs = "EPSG:27700"  # manual override - hosted data are Indexes which point to EPSG:4326
    # i = root.find(".//gmd:RS_Identifier/gmd:code/gco:CharacterString", xml_namespaces).text
    # crs = "EPSG:" + i.split("/")[-1]

    # get start and end dates
    date_end = None
    date_start = None

    # get licence
    licence = "Open Government Licence"  # metadata doesn't point to licence correctly
    # licence = root.find(".//gmd:useLimitation/gco:CharacterString", xml_namespaces).text,

    # use constraints
    use_constraints = ""
    # use_constraints = root.find(
    #         ".//gmd:otherConstraints/gco:CharacterString", xml_namespaces
    #     ).text

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
            ".//gmd:CI_Address/gmd:groupName/gco:CharacterString", xml_namespaces
        ).text,
        crs=crs,
        date_end=date_end,
        date_start=date_start,
        dem_type=dem_type,
        details="",
        format=data_format,
        host=root.find(
            ".//gmd:CI_Address/gmd:groupName/gco:CharacterString", xml_namespaces
        ).text,
        id=meta["id"],
        licence=licence,
        metadata_url=root.find(
            ".//gmd:CI_OnlineResource/gmd:linkage/gmd:URL", xml_namespaces
        ).text,
        title=root.find(".//gmd:title/gco:CharacterString", xml_namespaces).text,
        use_constraints=use_constraints,
    )
    return collection


def get_collections(ids: List[str] | None = None) -> List[DemCollection]:
    """
    Retrieves a list of available DEM collections from Data Map Wales (DMW).

    This function queries the DMW portal and returns a list of `DemCollection` instances
    representing each available collection, including associated metadata such as title, CRS, date
    range, and access URLs.

    Args:
        ids(List[DemCollection], optional): A list of collection ids to return.
            If not provided, returns all.

    Returns:
        List[DemCollection]: A list of DEM collections available from the DMW portal.
    """
    metas = [
        {
            "id": "welsh_government_lidar_tile_catalogue_2020_2023_dtm",
            "metadata_url": "https://datamap.gov.wales/catalogue/csw?"
            "request=GetRecordById&"
            "service=CSW&"
            "version=2.0.2&"
            "id=c00a927d-2705-4396-b9b3-3029c44ae367&"
            "outputschema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd&"
            "elementsetname=full",
        },
        {
            "id": "welsh_government_lidar_tile_catalogue_2020_2023_dsm",
            "metadata_url": "https://datamap.gov.wales/catalogue/csw?"
            "request=GetRecordById&"
            "service=CSW&"
            "version=2.0.2&"
            "id=c00a927d-2705-4396-b9b3-3029c44ae367&"
            "outputschema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd&"
            "elementsetname=full",
        },
        {
            "id": "nrw_lidar_tile_catalogue_archive_dtm",
            "metadata_url": "https://datamap.gov.wales/catalogue/csw?"
            "request=GetRecordById&"
            "service=CSW&"
            "version=2.0.2&"
            "id=2e6ee51a-a3de-4370-a991-e89e7e7f9ce4&"
            "outputschema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd&"
            "elementsetname=full",
        },
        {
            "id": "nrw_lidar_tile_catalogue_archive_dsm",
            "metadata_url": "https://datamap.gov.wales/catalogue/csw?"
            "request=GetRecordById&"
            "service=CSW&"
            "version=2.0.2&"
            "id=2e6ee51a-a3de-4370-a991-e89e7e7f9ce4&"
            "outputschema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd&"
            "elementsetname=full",
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


def get_data_intersecting_geometry(
    geometry: PolygonWKT, collections: list[str] | None = None
) -> List[DemTile]:
    """
    Retrieves DEM tiles from one or more collections that intersect a given polygon geometry.

    This function queries Data Map Wales and returns a list of `DemTile` objects representing data
    tiles that spatially intersect the input geometry. Optionally, you can limit the query to a
    specific subset of collections.

    Args:
        geometry (PolygonWKT): A PolygonWKT object to use for spatial intersection.
        collections (list[str], optional): A list of DEM collection IDs to filter the query.
            If not provided, all known collections will be queried.

    Returns:
        List[DemTile]: A list of `DemTile` instances that intersect the specified geometry.
    """
    # transform to EPSG:27700 to guarantee WFS request uses supported CRS
    geometry.transform(out_crs="EPSG:27700", replace=True)

    # get target collections (or all if not specified)
    _collections = get_collections(collections)
    tiles = []
    for collection in _collections:
        data = wfs_intersect_filter(
            geometry=geometry,
            wfs_url="https://datamap.gov.wales/geoserver/wfs",
            type_name=f"geonode:{collection.id[:-4]}",  # drop _dtm or _dsm from id
            property_name="geom",
            version="1.1.0",
            output_format="application/json",
        )
        match collection.format:
            case "GeoTIFF":
                file_type = ".tif"
            case "ASCII":
                file_type = ".asc"
            case _:
                file_type = None

        # loop through features
        unique_urls = (
            set()
        )  # track unique urls to prevent the same tile being used multiple times
        for i in data["features"]:
            if "date_flown" in i["properties"].keys():
                # format date and resolution and title
                date_split = i["properties"]["date_flown"].split("-")
                if date_split:
                    year = date_split[-1]
                    # check for double digit year format (i.e. 06 not 2006)
                    if len(year) == 2:
                        year_format = "%y"
                    else:
                        year_format = "%Y"

                    if len(date_split) >= 3:
                        # check if day is purely numeric
                        try:
                            int(date_split[-3])
                            day = date_split[-3]
                        except ValueError:
                            day = date_split[-3][:-2]
                            try:
                                day = int(day)
                            except ValueError:
                                day = 1  # no date provided, assume first day of month
                        month = date_split[-2]
                    else:
                        # no date provided, assume first day of month
                        day = 1
                        # parse month
                        month = date_split[0].split("/")[-1]

                    # get month format
                    if len(month) == 3:
                        month_format = "%b"
                    else:
                        month_format = "%B"
                    date = datetime.strptime(
                        f"{year}-{month}-{day}", f"{year_format}-{month_format}-%d"
                    )
                else:
                    date = None
                resolution = f"{i['properties']['resolution']}m"
                title = i["properties"]["gb_ng"]
            else:
                date = datetime.strptime(i["properties"]["date"], "%d-%m-%Y")
                resolution = "1m"
                title = i["properties"]["british_gr"]

            tile = DemTile(
                collection=collection,
                date=date,
                geometry=PolygonWKT.from_coordinates(
                    coordinates=i["geometry"]["coordinates"][0],
                    crs="EPSG:" + data["crs"]["properties"]["name"].split(":")[-1],
                ),
                resolution=resolution,
                size=0,
                title=title,
                type=file_type,
                url="",
            )

            _tile = copy(tile)
            if collection.id.endswith("dtm"):
                if "dtm_url" in i["properties"].keys():
                    if i["properties"]["dtm_url"]:
                        _tile.url = f"https://{i['properties']['dtm_url']}"
                elif "dtm_link" in i["properties"].keys():
                    if i["properties"]["dtm_link"]:
                        _tile.url = f"https://{i['properties']['dtm_link']}"
            elif collection.id.endswith("dsm"):
                if "dsm_url" in i["properties"].keys():
                    if i["properties"]["dsm_url"]:
                        _tile.url = f"https://{i['properties']['dsm_url']}"
                elif "dsm_link" in i["properties"].keys():
                    if i["properties"]["dsm_link"]:
                        _tile.url = f"https://{i['properties']['dsm_link']}"
            # only return tiles with urls not previously used
            if _tile.url not in unique_urls:
                unique_urls.add(_tile.url)
                tiles.append(_tile)
    return tiles


if __name__ == "__main__":
    wkt = "POLYGON ((324837.91116609796881676 187730.78707544109784067, 328510.40529526118189096 188431.32956430700141937, 328366.30463022610638291 186461.764554274501279, 325176.36712550360243767 186043.87840979505563155, 324837.91116609796881676 187730.78707544109784067))"
    crs = "epsg:27700"
    geometry = PolygonWKT(wkt, crs)
    result = get_data_intersecting_geometry(geometry)