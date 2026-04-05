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
    """Order polygon vertices using Shapely's Convex Hull algorithm.

    This eliminates self-intersecting (bowtie) polygons that arise when
    vertices are stored in arbitrary order.  Unlike the previous angular-sort
    approach, Convex Hull works correctly even when the centroid falls outside
    the polygon (concave input sets).

    Algorithm
    ---------
    1. Parse the coordinate string into ``(lat, lon)`` tuples.
    2. If fewer than 3 points, return the input unchanged (not a polygon).
    3. Remove duplicate points (preserving first occurrence order).
    4. If exactly 3 unique points remain, return them as-is (a triangle
       cannot self-intersect).
    5. Build a ``shapely.geometry.MultiPoint`` from the unique points,
       swapping to ``(lon, lat)`` order as required by Shapely's ``(x, y)``
       convention.
    6. Compute ``hull = multipoint.convex_hull``.
    7. If the hull is not a Polygon (e.g. collinear points yield a
       LineString), fall back to returning the deduplicated points in their
       original order.
    8. Extract the hull's exterior ring coordinates (dropping the closing
       duplicate), swap back to ``(lat, lon)`` order, and serialize.

    Parameters
    ----------
    coordenadas_str:
        String in the format ``'lat,lon | lat,lon | ...'``, or ``None``.

    Returns
    -------
    Ordered coordinate string in the same format, or the original value
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
    from shapely.geometry import MultiPoint  # noqa: PLC0415

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

    # Triangle: cannot self-intersect, return as-is
    if len(unique) == 3:
        return serializar_coordenadas(unique)

    # Build MultiPoint using Shapely's (x, y) = (lon, lat) convention
    multipoint = MultiPoint([(p[1], p[0]) for p in unique])
    hull = multipoint.convex_hull

    # Collinear points produce a LineString or Point — fall back to original order
    from shapely.geometry import Polygon as _Polygon  # noqa: PLC0415

    if not isinstance(hull, _Polygon):
        return serializar_coordenadas(unique)

    # Extract exterior ring, drop closing duplicate, swap back to (lat, lon)
    hull_coords = list(hull.exterior.coords)[:-1]
    ordered = [(lat, lon) for lon, lat in hull_coords]

    return serializar_coordenadas(ordered)


def validar_geometria(
    coordenadas_str: Optional[str],
    superficie_reportada: Optional[float] = None,
) -> tuple:
    """Validate that a coordinate string represents a usable polygon geometry.

    Parameters
    ----------
    coordenadas_str:
        String in the format ``'lat,lon | lat,lon | ...'``, or ``None``.
    superficie_reportada:
        Optional reported area in hectares (from the Excel ``superficie``
        field).  Reserved for future cross-checks; not used in current rules.

    Returns
    -------
    ``(es_valido, motivo)`` where *es_valido* is ``True`` when the geometry
    passes all checks and *motivo* is a human-readable failure reason (empty
    string when valid).

    Validation rules (checked in order, returns on first failure)
    -------------------------------------------------------------
    1. Sin coordenadas   – None / empty / whitespace-only input.
    2. Punto único       – only 1 coordinate after parsing.
    3. Línea             – only 2 coordinates after parsing.
    4. Coordenadas duplicadas – 3+ coords but fewer than 3 unique ones.
    5. Área cero         – Shapely polygon area == 0.
    6. Geometría inválida irreparable – Shapely ``is_valid`` is False AND
       ``buffer(0)`` yields an empty geometry.
    7. Área excesiva     – calculated area > 1000 ha.
    """
    # ------------------------------------------------------------------ #
    # Rule 1 – Sin coordenadas                                            #
    # ------------------------------------------------------------------ #
    if coordenadas_str is None or not str(coordenadas_str).strip():
        return (False, "Sin coordenadas")

    # ------------------------------------------------------------------ #
    # Parse                                                               #
    # ------------------------------------------------------------------ #
    coords = parsear_coordenadas(coordenadas_str)

    # ------------------------------------------------------------------ #
    # Rule 2 – Punto único                                                #
    # ------------------------------------------------------------------ #
    if len(coords) == 1:
        return (False, "Solo un punto, no es polígono")

    # ------------------------------------------------------------------ #
    # Rule 3 – Línea                                                      #
    # ------------------------------------------------------------------ #
    if len(coords) == 2:
        return (False, "Solo dos puntos, es una línea")

    # ------------------------------------------------------------------ #
    # Rule 4 – Coordenadas duplicadas                                     #
    # ------------------------------------------------------------------ #
    unique_coords = list({(p[0], p[1]) for p in coords})
    if len(unique_coords) < 3:
        return (False, "Coordenadas duplicadas, no forma polígono")

    # ------------------------------------------------------------------ #
    # Build Shapely polygon (lon, lat) — import at function level         #
    # ------------------------------------------------------------------ #
    from shapely.geometry import Polygon as ShapelyPolygon  # noqa: PLC0415

    # Convert [lat, lon] → (lon, lat) for Shapely (x=lon, y=lat)
    ring = [(p[1], p[0]) for p in coords]

    # Close the ring if necessary
    if ring[0] != ring[-1]:
        ring.append(ring[0])

    polygon = ShapelyPolygon(ring)

    # ------------------------------------------------------------------ #
    # Rule 5 – Área cero                                                  #
    # ------------------------------------------------------------------ #
    if polygon.area == 0:
        return (False, "Área cero, polígono degenerado")

    # ------------------------------------------------------------------ #
    # Rule 6 – Geometría inválida irreparable                             #
    # ------------------------------------------------------------------ #
    if not polygon.is_valid:
        repaired = polygon.buffer(0)
        if repaired.is_empty:
            return (False, "Geometría inválida irreparable")
        # Use the repaired polygon for the area check below
        polygon = repaired

    # ------------------------------------------------------------------ #
    # Rule 7 – Área excesiva (>1000 ha)                                   #
    # ------------------------------------------------------------------ #
    # Approximate area in hectares using a degree-to-metre conversion.
    # cos(mean_lat) corrects for longitude compression at higher latitudes.
    # Accuracy is sufficient for detecting gross coordinate errors.
    lats = [p[0] for p in coords]
    mean_lat_rad = math.radians(sum(lats) / len(lats))
    # shapely area is in degrees²; convert to m² then to ha
    area_ha = polygon.area * (111_320**2) * math.cos(mean_lat_rad) / 10_000
    if area_ha > 1000:
        return (False, "Área excesiva (>1000 ha), posible error de coordenadas")

    return (True, "")
