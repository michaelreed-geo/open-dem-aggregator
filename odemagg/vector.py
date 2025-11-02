"""
Module for handling vector geometry and associated transforms that are used for spatial queries of
DEM data.
"""

from typing import List

from pyproj import Transformer
from pyproj.crs import CRS


def wkt_is_polygon(geometry: str) -> bool:
    """
    Checks whether the given WKT (Well-Known Text) string represents a polygon or multipolygon
    geometry.

    This function returns True if the geometry type is POLYGON and raises a ValueError if the input
    is not a valid POLYGON WKT.

    Args:
        geometry (str): A WKT-formatted geometry string.

    Returns:
        bool: True if the WKT represents a polygon or multipolygon.

    Raises:
        ValueError: If the input string is not a valid WKT geometry.
    """
    if not isinstance(geometry, str):
        raise ValueError("Geometry is not str.")
    # check WKT begins with POLYGON
    if not geometry.upper().startswith("POLYGON"):
        raise ValueError("Geometry is not of POLYGON type.")
    # check POLYGON is followed by ((
    if not geometry[7:].strip().startswith("(("):
        raise ValueError(
            "Invalid geometry format. Must contain double brackets `((` following POLYGON at start"
            "of string."
        )
    # check string ends with ))
    if not geometry.endswith("))"):
        raise ValueError("Invalid geometry format. Must end with double brackets `))`.")
    # check coordinates
    ring_coords = geometry[geometry.find("((") + 2 : geometry.find("))")]
    first_coord = ()
    last_coord = ()
    # TODO: check for internal duplicates in ring?
    for i, j in enumerate(ring_coords.split(",")):
        j = j.strip()  # clean up leading or trailing spaces
        # check coordinates are in pairs
        if not len(j.split(" ")) == 2:
            raise ValueError(
                f"Pairs of coordinate expected. At index={i}, coordinates of {j} found instead."
            )
        # check coordinates are purely numeric
        for k in j.split(" "):
            try:
                float(k)
            except ValueError as exc:
                raise ValueError(
                    f"Non-numeric value at index={i}, coordinate value of {j}."
                ) from exc
        if i == 0:
            first_coord = j.split(" ")
        if i == len(ring_coords.split(",")) - 1:
            last_coord = j.split(" ")
    # check first coordinate == last coordinate
    if first_coord != last_coord:
        raise ValueError(
            "First coordinate pair and last coordinate pair must be identical."
        )
    return True  # only returns if all tests pass


def get_bounds(
    geometry: str, accuracy: int | None = None
) -> tuple[float, float, float, float]:
    """
    Gets the bounding box for a geometry.

    Args:
        geometry (str): WKT representation of a polygon geometry.
        accuracy (int or None, optional): Number of decimal places to round the bounding box
            coordinates. If None, no rounding is applied. Defaults to None.

    Returns:
        tuple[float, float, float, float]: Bounding box as (x_min, y_min, x_max, y_max).
    """
    wkt_is_polygon(geometry)  # check geometry is valid polygon WKT, raises error if not
    ring_coords = geometry[geometry.find("((") + 2 : geometry.find("))")]
    x_min, y_min, x_max, y_max = (
        float("inf"),
        float("inf"),
        float("-inf"),
        float("-inf"),
    )
    # loop through coordinates and compute bounds
    for i in ring_coords.split(","):
        i = i.strip()  # clean up leading or trailing spaces
        x, y = map(float, i.split(" "))
        x_min = min(x_min, x)
        y_min = min(y_min, y)
        x_max = max(x_max, x)
        y_max = max(y_max, y)
    # adjust accuracy if required
    if accuracy:
        x_min = round(x_min, accuracy)
        y_min = round(y_min, accuracy)
        x_max = round(x_max, accuracy)
        y_max = round(y_max, accuracy)
    return x_min, y_min, x_max, y_max


def transform_polygon(
    geometry: str,
    in_crs: CRS | str,
    out_crs: CRS | str,
    accuracy: int | None = None,
    always_xy: bool = True,
) -> str:
    """
    Transforms a polygon from one coordinate reference system (CRS) to another.

    Args:
        geometry (str): WKT representation of a polygon geometry.
        in_crs (CRS or str): CRS used to define the input geometry.
        out_crs (CRS or str): CRS to transform the geometry into.
        accuracy (int or None, optional): Number of decimal places to round output coordinates to.
            If None, no rounding is applied. Defaults to None.
        always_xy (bool, optional): If True, coordinates are treated as (longitude, latitude) or
            (easting, northing). See pyproj.Transformer documentation for details. Defaults to True.

    Returns:
        str: WKT representation of the transformed geometry.
    """
    wkt_is_polygon(geometry)  # check geometry is valid polygon WKT, raises error if not
    if in_crs != out_crs:
        transformer = Transformer.from_crs(in_crs, out_crs, always_xy=always_xy)
        transformed_geometry = "POLYGON (("
        ring_coords = geometry[geometry.find("((") + 2 : geometry.find("))")]
        for i in ring_coords.split(","):
            i = i.strip()  # clean up leading or trailing spaces
            x, y = i.split(" ")
            x, y = float(x), float(y)
            x_trans, y_trans = transformer.transform(x, y)
            if accuracy:
                # if accuracy specified, round to it
                transformed_geometry += (
                    f"{x_trans:.{accuracy}f} {y_trans:.{accuracy}f},"
                )
            else:
                # if no accuracy specified, leave as default
                transformed_geometry += f"{x_trans} {y_trans},"
        transformed_geometry = transformed_geometry[:-1] + "))"
    else:
        # CRS match - no need to transform
        transformed_geometry = geometry
    return transformed_geometry


class PolygonWKT:
    """
    A class for representing and manipulating polygon geometries in WKT (Well-Known Text) format.

    This class encapsulates a WKT polygon string along with its associated coordinate reference
    system (CRS). It provides utility properties and methods to access bounds, coordinates, and
    perform CRS transformations.

    Attributes:
        geometry (str): The polygon geometry in WKT format.
        crs (CRS | str): The coordinate reference system associated with the geometry.

    Methods:
        bounds: Returns the bounding box of the polygon as a tuple (xmin, ymin, xmax, ymax).
        coordinates: Returns a list of (x, y) tuples representing the exterior ring of the polygon.
        transform: Transforms the geometry to a new CRS, optionally replacing the current geometry
            and CRS.
    """

    def __init__(self, geometry: str, crs: CRS | str):
        """
        Initializes a PolygonWKT object with its associated coordinate reference system (CRS).

        Args:
            geometry (str): WKT representation of a polygon geometry.
            crs (CRS or str): CRS used to define the geometry.
        """
        wkt_is_polygon(
            geometry
        )  # check geometry is valid polygon WKT, raises error if not
        self.geometry = geometry.upper()
        if isinstance(crs, str):
            # convert to pyproj.crs.CRS to ensure valid projection
            self.crs = CRS(crs)
        else:
            self.crs = crs

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """
        Returns the bounding box of the polygon geometry.

        Returns:
            tuple[float, float, float, float]: Bounding box as (x_min, y_min, x_max, y_max).
        """
        return get_bounds(self.geometry)

    @property
    def coordinates(self) -> list[tuple[float, float]]:
        """
        Returns a list of coordinates for the exterior ring of the polygon geometry.

        Returns:
            list[tuple[float, float]]: List of (x, y) coordinate tuples representing the polygon’s
                exterior ring.
        """
        ring_coords = self.geometry[
            self.geometry.find("((") + 2 : self.geometry.find("))")
        ]
        coordinates = []
        for i in ring_coords.split(","):
            i = i.strip()  # clean up leading or trailing spaces
            x, y = i.split(" ")
            coordinates.append((float(x), float(y)))
        return coordinates

    def transform(
        self,
        out_crs: CRS | str,
        accuracy: int | None = None,
        always_xy: bool = True,
        replace: bool = False,
    ) -> "PolygonWKT":
        """
        Transforms geometry from the current CRS to a new CRS.

        Args:
            out_crs (CRS or str): CRS to transform the geometry into.
            accuracy (int or None, optional): Number of decimal places to round output coordinates
                to. If None, no rounding is applied. Defaults to None.
            always_xy (bool, optional): If True, coordinates are treated as (longitude, latitude) or
                (easting, northing). See pyproj.transform.Transformer documentation for details.
                Defaults to True.
            replace (bool, optional):
                If True, replaces the geometry and CRS of the current object with the transformed
                values.
                If False, returns a new PolygonWKT object with the transformed geometry.
                Defaults to False.

        Returns:
            PolygonWKT or self: The transformed geometry as a PolygonWKT object,
                or self if `replace` is True.
        """
        if isinstance(out_crs, str):
            # convert to pyproj.crs.CRS to ensure valid projection
            out_crs = CRS(out_crs)

        transformed = PolygonWKT(
            geometry=transform_polygon(
                geometry=self.geometry,
                in_crs=self.crs,
                out_crs=out_crs,
                accuracy=accuracy,
                always_xy=always_xy,
            ),
            crs=out_crs,
        )
        if replace:
            # replace the current geometry and crs with the transformed values
            self.geometry = transformed.geometry
            self.crs = out_crs
            return self
        return transformed

    @classmethod
    def from_coordinates(
        cls, coordinates: List[tuple[float, float]], crs: CRS | str
    ) -> "PolygonWKT":
        """
        Creates a PolygonWKT object from a list of (x, y) coordinates.

        The coordinates should define the exterior ring of the polygon. If the first and last points
        are not the same, the method will automatically close the ring.

        Args:
            coords (list[tuple[float, float]]): List of (x, y) tuples defining the polygon boundary.
            crs (CRS or str): Coordinate reference system for the geometry.

        Returns:
            PolygonWKT: A new PolygonWKT instance constructed from the provided coordinates.
        """
        if len(coordinates) < 3:
            raise ValueError("At least 3 coordinates are required to form a polygon.")

        # Close the ring if not already closed
        if coordinates[0] != coordinates[-1]:
            coordinates.append(coordinates[0])

        coord_str = ", ".join(f"{x} {y}" for x, y in coordinates)
        wkt = f"POLYGON (({coord_str}))"
        return cls(wkt, crs)

    @classmethod
    def from_bounds(
        cls, bounds: tuple[float, float, float, float], crs: CRS | str
    ) -> "PolygonWKT":
        """

        Args:
            bounds:
            crs:

        Returns:

        """
        x_min, y_min, x_max, y_max = bounds
        coords = [
            (x_min, y_min),
            (x_min, y_max),
            (x_max, y_max),
            (x_max, y_min),
            (x_min, y_min),
        ]
        return cls.from_coordinates(coords, crs)

    def contains(
        self, x: float, y: float, crs: CRS | str | None = None, always_xy: bool = True
    ) -> bool:
        # default to using same CRS as polygon
        if not crs:
            crs = self.crs
        # transform coordinate to polygon CRS
        if isinstance(crs, str):
            # convert to pyproj.crs.CRS to ensure valid projection
            crs = CRS(crs)
        if crs != self.crs:
            transformer = Transformer.from_crs(crs, self.crs, always_xy=always_xy)
            x, y = transformer.transform(x, y)

        contains = False
        coord_count = len(self.coordinates)

        for i in range(coord_count):
            x1, y1 = self.coordinates[i]
            x2, y2 = self.coordinates[(i + 1) % coord_count]

            # Check if point is on an edge (inclusive test)
            if (
                (y - y1) * (x2 - x1) == (x - x1) * (y2 - y1)
                and min(x1, x2) <= x <= max(x1, x2)
                and min(y1, y2) <= y <= max(y1, y2)
            ):
                return True
            # Ray casting: check if edge crosses horizontal ray at y
            if (y1 > y) != (y2 > y):  # edge straddles y
                x_intersect = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
                if x_intersect == x:  # directly on edge
                    return True
                if x_intersect > x:  # edge crosses ray to the right
                    contains = not contains
        return contains

    @property
    def centroid(self) -> tuple[float, float]:
        coords = self.coordinates
        if coords[0] == coords[-1]:
            coords = coords[:-1]  # drop duplicate closing point
        n = len(coords)
        if n < 3:
            raise ValueError("A polygon must have at least 3 distinct vertices.")

        area = 0.0
        cx = 0.0
        cy = 0.0

        for i in range(n):
            x0, y0 = coords[i]
            x1, y1 = coords[(i + 1) % n]
            cross = x0 * y1 - x1 * y0
            area += cross
            cx += (x0 + x1) * cross
            cy += (y0 + y1) * cross

        area *= 0.5
        if area == 0:
            raise ValueError("Degenerate polygon with zero area.")

        cx /= (6.0 * area)
        cy /= (6.0 * area)
        return cx, cy
