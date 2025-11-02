"""
Module for handling interactions with the OGC Web Services, in particular WFS.
"""

import json
import urllib.parse

from odemagg.vector import PolygonWKT
from odemagg.web import https_request


def wfs_intersect_filter(
    geometry: PolygonWKT,
    wfs_url: str,
    type_name: str,
    property_name: str,
    version: str = "1.1.0",
    output_format: str = "application/json",
) -> dict | str:
    """
    Perform a WFS GetFeature request with an Intersects spatial filter.

    Constructs and sends a WFS GetFeature request to the specified WFS server URL,
    filtering features that spatially intersect the given polygon geometry. The
    geometry is encoded as a GML Polygon in the filter.

    Args:
        geometry (PolygonWKT): Polygon geometry with coordinates and CRS to use in the spatial
            filter.
        wfs_url (str): Base URL of the WFS service endpoint.
        type_name (str): The WFS feature type name (e.g., 'geonode:layer_name').
        property_name (str): The geometry property name in the feature type (e.g., 'geom').
        version (str, optional): WFS service version. Defaults to "1.1.0".
        output_format (str, optional): Desired output format of the WFS response.
            Defaults to "application/json" (GeoJSON).

    Returns:
        dict or str: Parsed GeoJSON dictionary if `output_format` is "application/json",
        otherwise the raw response string.

    Raises:
        (Depending on `https_request`) Exceptions related to network or HTTP errors.
    """
    # build the geometry filter
    wfs_filter = (
        "<Filter>"
        "<Intersects>"
        f"<PropertyName>{property_name}</PropertyName>"
        f'<gml:Polygon srsName="{geometry.crs.srs}" xmlns:gml="http://www.opengis.net/gml">'
        "<gml:exterior>"
        "<gml:LinearRing>"
        "<gml:posList>"
        f"{' '.join([str(i[0]) + ' ' + str(i[1]) for i in geometry.coordinates])}"
        "</gml:posList>"
        "</gml:LinearRing>"
        "</gml:exterior>"
        "</gml:Polygon>"
        "</Intersects>"
        "</Filter>"
    )
    parameters = {
        "service": "wfs",
        "version": version,
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": output_format,
        "filter": urllib.parse.quote(wfs_filter),
    }
    query = ""
    for i, j in parameters.items():
        query += f"{i}={j}&"
    query = query[:-1]
    query_url = f"{wfs_url}?{query}"
    data = https_request(query_url)

    # format output
    if output_format == "application/json":
        data = json.loads(data)
    return data
