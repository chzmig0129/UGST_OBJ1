"""
tests/test_geometry.py
----------------------
Unit tests for ``ordenar_coordenadas()``.

Covers:
- Convex Hull fallback for bowtie/self-intersecting polygons (UGST_OBJ1-0i7.1)
- Concave vertex preservation for valid user-edited polygons (UGST_OBJ1-rhk)

Run with:
    pytest tests/test_geometry.py
"""

import pytest
from shapely.geometry import Polygon

from utils.geometry import ordenar_coordenadas, parsear_coordenadas


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_polygon(coord_str: str) -> Polygon:
    """Parse a coordinate string and return a Shapely Polygon.

    Coordinates are stored as ``lat,lon`` but Shapely expects ``(x, y) =
    (lon, lat)``, so we swap the pair order here.
    """
    coords = parsear_coordenadas(coord_str)
    return Polygon([(c[1], c[0]) for c in coords])


# ---------------------------------------------------------------------------
# Test 1 — None input
# ---------------------------------------------------------------------------


def test_none_input():
    """ordenar_coordenadas(None) must return None."""
    assert ordenar_coordenadas(None) is None


# ---------------------------------------------------------------------------
# Test 2 — Empty string
# ---------------------------------------------------------------------------


def test_empty_string():
    """ordenar_coordenadas('') must return an empty string."""
    result = ordenar_coordenadas("")
    assert result == ""


# ---------------------------------------------------------------------------
# Test 3 — Single point
# ---------------------------------------------------------------------------


def test_single_point():
    """A single-point string is returned unchanged (not a polygon)."""
    single = "17.615014,-93.493808"
    result = ordenar_coordenadas(single)
    # The function returns the original string for < 3 points
    assert result == single


# ---------------------------------------------------------------------------
# Test 4 — Two points
# ---------------------------------------------------------------------------


def test_two_points():
    """A two-point string is returned unchanged (not a polygon)."""
    two = "17.615014,-93.493808 | 17.608478,-93.489739"
    result = ordenar_coordenadas(two)
    assert result == two


# ---------------------------------------------------------------------------
# Test 5 — Triangle (three points)
# ---------------------------------------------------------------------------


def test_triangle():
    """Three points form a valid triangle; the function must not crash."""
    triangle = "17.615014,-93.493808 | 17.608478,-93.489739 | 17.614461,-93.486269"
    result = ordenar_coordenadas(triangle)
    assert result is not None

    poly = _to_polygon(result)
    assert poly.is_valid, "Triangle polygon must be valid"


# ---------------------------------------------------------------------------
# Test 6 — Bowtie square (the canonical failing case)
# ---------------------------------------------------------------------------


def test_bowtie_square():
    """Four points that form a bowtie with angular sort produce a valid convex polygon.

    The input vertices are in an order that would create a self-intersecting
    (bowtie) polygon if simply connected in sequence.  The Convex Hull
    algorithm must reorder them into a non-self-intersecting polygon.
    """
    bowtie_input = (
        "17.615014,-93.493808 | "
        "17.608478,-93.489739 | "
        "17.614461,-93.486269 | "
        "17.610058,-93.494614"
    )
    result = ordenar_coordenadas(bowtie_input)
    assert result is not None

    poly = _to_polygon(result)

    # Primary assertion: polygon must be valid (no self-intersections)
    assert poly.is_valid, (
        f"Bowtie polygon must be valid after reordering, got: {result}"
    )

    # Explicit check: polygon must be simple (no self-intersections)
    assert poly.is_simple, f"Bowtie polygon must not self-intersect, got: {result}"


# ---------------------------------------------------------------------------
# Test 7 — Concave staircase / L-shape (UGST_OBJ1-rhk regression)
# ---------------------------------------------------------------------------


def test_concave_staircase():
    """Points forming a valid L-shape must have ALL vertices preserved.

    The six input points form a concave (but non-self-intersecting) polygon.
    The fix in UGST_OBJ1-rhk ensures the function returns the polygon as-is
    instead of applying convex hull and silently dropping the concave vertex.

    Assertions
    ----------
    - Output parses to the same number of unique vertices as input (no drops).
    - The concave vertex (1.0, 1.0) is still present in the output.
    - The resulting polygon is valid and non-self-intersecting.
    """
    # Six points forming an L-shape staircase (lat,lon using small values).
    # Connected in order these form a valid concave polygon — no self-intersections.
    staircase = (
        "0.000000,0.000000 | "
        "0.000000,2.000000 | "
        "1.000000,2.000000 | "
        "1.000000,1.000000 | "  # concave vertex — must be preserved
        "2.000000,1.000000 | "
        "2.000000,0.000000"
    )
    result = ordenar_coordenadas(staircase)
    assert result is not None

    input_coords = parsear_coordenadas(staircase)
    output_coords = parsear_coordenadas(result)

    # Same number of unique vertices — no drops
    input_unique = {(round(c[0], 6), round(c[1], 6)) for c in input_coords}
    output_unique = {(round(c[0], 6), round(c[1], 6)) for c in output_coords}

    assert len(output_unique) == len(input_unique), (
        f"Concave polygon must preserve all {len(input_unique)} vertices, "
        f"got {len(output_unique)}: {result}"
    )

    # The concave vertex must still be present
    concave_vertex = (1.0, 1.0)
    assert concave_vertex in output_unique, (
        f"Concave vertex {concave_vertex} was dropped. Output: {result}"
    )

    # The resulting polygon must still be valid (no self-intersections)
    poly = _to_polygon(result)
    assert poly.is_valid, (
        f"Concave staircase polygon must be valid, got: {result}"
    )
    assert poly.is_simple, f"Concave staircase polygon must not self-intersect, got: {result}"


# ---------------------------------------------------------------------------
# Test 8 — Duplicate points are removed
# ---------------------------------------------------------------------------


def test_duplicates_removed():
    """Input with duplicate points still produces a valid polygon.

    The duplicate is silently removed before the hull is computed.
    """
    # Four unique hull vertices + one duplicate of the first
    with_dupes = (
        "17.615014,-93.493808 | "
        "17.608478,-93.489739 | "
        "17.614461,-93.486269 | "
        "17.615014,-93.493808 | "  # duplicate
        "17.610058,-93.494614"
    )
    result = ordenar_coordenadas(with_dupes)
    assert result is not None

    poly = _to_polygon(result)
    assert poly.is_valid, (
        f"Polygon with duplicates removed must be valid, got: {result}"
    )


# ---------------------------------------------------------------------------
# Test 9 — Collinear points (graceful handling)
# ---------------------------------------------------------------------------


def test_collinear_points():
    """Three or more collinear points must not raise an exception.

    The convex hull of collinear points is a LineString, not a Polygon.
    The function falls back to returning the deduplicated points in their
    original order rather than crashing.
    """
    collinear = "0.0,0.0 | 1.0,0.0 | 2.0,0.0 | 3.0,0.0"
    # Must not raise
    result = ordenar_coordenadas(collinear)
    assert result is not None, "Collinear input must not return None"
    # Result must be parseable
    coords = parsear_coordenadas(result)
    assert len(coords) >= 3, "Collinear fallback must preserve at least 3 points"


# ---------------------------------------------------------------------------
# Test 10 — All convex hull vertices are present in the output
# ---------------------------------------------------------------------------


def test_preserves_all_hull_vertices():
    """Every vertex of the convex hull must appear in the output.

    For a set of four points that are all on the convex hull (no interior
    points), the output must contain exactly those four points.
    """
    bowtie_input = (
        "17.615014,-93.493808 | "
        "17.608478,-93.489739 | "
        "17.614461,-93.486269 | "
        "17.610058,-93.494614"
    )
    result = ordenar_coordenadas(bowtie_input)
    assert result is not None

    input_coords = parsear_coordenadas(bowtie_input)
    output_coords = parsear_coordenadas(result)

    # Round to 6 dp to avoid floating-point noise
    input_set = {(round(c[0], 6), round(c[1], 6)) for c in input_coords}
    output_set = {(round(c[0], 6), round(c[1], 6)) for c in output_coords}

    assert output_set == input_set, (
        f"All hull vertices must be present in output.\n"
        f"  Input:  {sorted(input_set)}\n"
        f"  Output: {sorted(output_set)}"
    )
