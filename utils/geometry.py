"""
utils/geometry.py
-----------------
Utility functions for coordinate string parsing, serialization, and angular
sorting to eliminate self-intersecting (bowtie) polygons.

Only the standard-library ``math`` module is used — no numpy, shapely, flask,
or sqlalchemy dependencies.
"""

import math
from typing import List, Optional, Union


def parsear_coordenadas(coordenadas_str: Optional[str]) -> List[List[float]]:
    """Parse a coordinate string into a list of [lat, lon] float pairs.

    Parameters
    ----------
    coordenadas_str:
        String in the format ``'lat,lon | lat,lon | ...'``.
        Whitespace around each token is stripped.

    Returns
    -------
    list of [lat, lon] pairs.  Returns an empty list for empty/None input or
    when no valid pairs can be parsed.

    Examples
    --------
    >>> parsear_coordenadas('17.608478,-93.489739 | 17.610058,-93.494614')
    [[17.608478, -93.489739], [17.610058, -93.494614]]
    >>> parsear_coordenadas('')
    []
    >>> parsear_coordenadas(None)
    []
    """
    if not coordenadas_str:
        return []

    result: List[List[float]] = []
    for token in coordenadas_str.split("|"):
        token = token.strip()
        if "," not in token:
            continue
        parts = token.split(",", 1)
        try:
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            result.append([lat, lon])
        except (ValueError, IndexError):
            continue  # skip invalid pairs silently

    return result


def serializar_coordenadas(coords_list: List[Union[List[float], tuple]]) -> str:
    """Serialize a list of coordinate pairs back to the canonical string format.

    Parameters
    ----------
    coords_list:
        List of ``[lat, lon]`` or ``(lat, lon)`` pairs.

    Returns
    -------
    String in the format ``'lat,lon | lat,lon | ...'`` with 6 decimal places.

    Examples
    --------
    >>> serializar_coordenadas([[17.608478, -93.489739]])
    '17.608478,-93.489739'
    >>> serializar_coordenadas([[17.608478, -93.489739], [17.610058, -93.494614]])
    '17.608478,-93.489739 | 17.610058,-93.494614'
    """
    tokens = [f"{lat:.6f},{lon:.6f}" for lat, lon in coords_list]
    return " | ".join(tokens)


def ordenar_coordenadas(coordenadas_str: Optional[str]) -> Optional[str]:
    """Sort polygon vertices angularly around their centroid (counter-clockwise).

    This eliminates self-intersecting (bowtie) polygons that arise when
    vertices are stored in arbitrary order.

    Algorithm
    ---------
    1. Parse the coordinate string into ``(lat, lon)`` tuples.
    2. If fewer than 3 points, return the input unchanged (not a polygon).
    3. Remove duplicate points (preserving first occurrence order).
    4. Compute the centroid as the arithmetic mean of all latitudes and
       longitudes.
    5. For each point compute the angle from the centroid using
       ``math.atan2(lat - centroid_lat, lon - centroid_lon)``.
    6. Sort points by angle ascending (counter-clockwise order).
    7. Serialize back to ``'lat,lon | lat,lon | ...'`` with 6 decimal places.

    Parameters
    ----------
    coordenadas_str:
        String in the format ``'lat,lon | lat,lon | ...'``, or ``None``.

    Returns
    -------
    Sorted coordinate string in the same format, or the original value
    unchanged when the input is empty/None or has fewer than 3 points.

    Examples
    --------
    >>> # Bowtie example — four points in arbitrary order
    >>> result = ordenar_coordenadas(
    ...     '17.615014,-93.493808 | 17.608478,-93.489739 | '
    ...     '17.614461,-93.486269 | 17.610058,-93.494614'
    ... )
    >>> # Result is a convex ordering with no self-intersections
    """
    # Edge case: empty or None
    if coordenadas_str is None:
        return None
    if coordenadas_str == "":
        return ""

    # Parse
    parsed = parsear_coordenadas(coordenadas_str)

    # Fewer than 3 points → not a polygon, return unchanged
    if len(parsed) < 3:
        return coordenadas_str

    # Remove duplicates while preserving order
    seen: dict = {}
    unique: List[List[float]] = []
    for pair in parsed:
        key = (pair[0], pair[1])
        if key not in seen:
            seen[key] = True
            unique.append(pair)

    # Still fewer than 3 after dedup → return unchanged
    if len(unique) < 3:
        return coordenadas_str

    # Centroid
    n = len(unique)
    centroid_lat = sum(p[0] for p in unique) / n
    centroid_lon = sum(p[1] for p in unique) / n

    # Angular sort (counter-clockwise)
    def angle_key(point: List[float]) -> float:
        return math.atan2(point[0] - centroid_lat, point[1] - centroid_lon)

    sorted_coords = sorted(unique, key=angle_key)

    return serializar_coordenadas(sorted_coords)
