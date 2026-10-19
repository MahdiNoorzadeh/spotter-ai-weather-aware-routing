"""Geometry calculations for locating checkpoint coordinates along GeoJSON lines."""

from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from api.providers.base import GeoPoint

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1 = a
    lon2, lat2 = b
    lat1_r, lat2_r = radians(lat1), radians(lat2)
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    value = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * asin(min(1.0, sqrt(value)))


def point_at_distance(coordinates: list, mile_marker: float) -> GeoPoint:
    if not coordinates:
        raise ValueError("Route geometry has no coordinates")
    if mile_marker <= 0 or len(coordinates) == 1:
        return GeoPoint(float(coordinates[0][1]), float(coordinates[0][0]))
    cumulative = 0.0
    for left, right in zip(coordinates, coordinates[1:], strict=False):
        segment = haversine_miles(
            (float(left[0]), float(left[1])),
            (float(right[0]), float(right[1])),
        )
        if cumulative + segment >= mile_marker:
            fraction = 0.0 if segment == 0 else (mile_marker - cumulative) / segment
            return GeoPoint(
                lat=float(left[1]) + fraction * (float(right[1]) - float(left[1])),
                lon=float(left[0]) + fraction * (float(right[0]) - float(left[0])),
            )
        cumulative += segment
    last = coordinates[-1]
    return GeoPoint(float(last[1]), float(last[0]))
