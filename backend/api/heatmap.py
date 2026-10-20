"""Build a preloaded 49-frame weather-risk heatmap for route corridors."""

from __future__ import annotations

from datetime import datetime, timedelta
from math import cos, hypot, radians
from typing import Any, cast

from api.errors import GeocodingError, RoutingError, WeatherProviderError
from api.geometry import point_at_distance
from api.providers.base import GeoPoint, RouteCandidate
from api.providers.geocoding import NominatimGeocodingProvider
from api.providers.routing import FallbackRoutingProvider
from api.providers.weather import OpenMeteoWeatherProvider
from routing.risk import RiskLevel, assess_weather

FRAME_COUNT = 49
FRAME_HOURS = range(FRAME_COUNT)
DEFAULT_SAMPLE_INTERVAL_MILES = 20
CORRIDOR_HALF_WIDTH_MILES = 3.0
MILES_PER_LATITUDE_DEGREE = 69.0


def _resolve_location(
    value: str | None,
    lat: float | None,
    lon: float | None,
    geocoder: NominatimGeocodingProvider,
) -> GeoPoint:
    if lat is not None and lon is not None:
        return GeoPoint(float(lat), float(lon), value or "")
    if not value:
        raise GeocodingError("Provide a place name or a latitude/longitude pair")
    suggestions = geocoder.search(value, limit=1)
    if not suggestions:
        raise GeocodingError(f"Could not find a location matching '{value}'")
    return suggestions[0].point


def _corridor_points(candidate: RouteCandidate, interval_miles: int) -> list[GeoPoint]:
    """Sample route centerline and two points 3 miles to either side."""
    distance = candidate.distance_mi
    coordinates = cast(
    list[list[float]],
    candidate.geometry["coordinates"],
    )
    markers = [float(mile) for mile in range(0, int(distance), interval_miles)]
    if not markers or markers[0] != 0:
        markers.insert(0, 0.0)
    if markers[-1] != distance:
        markers.append(distance)

    result: list[GeoPoint] = []
    for marker in markers:
        center = point_at_distance(coordinates, marker)
        result.append(center)

        # Estimate the local direction using points on either side of the marker.
        before = point_at_distance(coordinates, max(0.0, marker - 0.5))
        after = point_at_distance(coordinates, min(distance, marker + 0.5))
        mean_lat = radians(center.lat)
        dx = (after.lon - before.lon) * cos(mean_lat) * MILES_PER_LATITUDE_DEGREE
        dy = (after.lat - before.lat) * MILES_PER_LATITUDE_DEGREE
        magnitude = hypot(dx, dy)
        if magnitude < 1e-9:
            continue
        # The normal vector (-dy, dx) is perpendicular to the local route tangent.
        normal_x, normal_y = -dy / magnitude, dx / magnitude
        lat_offset = normal_y * CORRIDOR_HALF_WIDTH_MILES / MILES_PER_LATITUDE_DEGREE
        lon_scale = max(cos(mean_lat) * MILES_PER_LATITUDE_DEGREE, 1e-6)
        lon_offset = normal_x * CORRIDOR_HALF_WIDTH_MILES / lon_scale
        for sign in (-1, 1):
            lat = max(-90.0, min(90.0, center.lat + sign * lat_offset))
            lon = max(-180.0, min(180.0, center.lon + sign * lon_offset))
            result.append(GeoPoint(lat, lon, center.label))
    return result


def build_heatmap(
    *,
    origin: str | None,
    destination: str | None,
    origin_lat: float | None,
    origin_lon: float | None,
    destination_lat: float | None,
    destination_lon: float | None,
    departure_time: datetime,
    load_weight_lb: float,
    sample_interval_miles: int = DEFAULT_SAMPLE_INTERVAL_MILES,
) -> dict[str, Any]:
    """Return all 49 forecast frames for a route corridor in GeoJSON form."""
    geocoder = NominatimGeocodingProvider()
    routing = FallbackRoutingProvider()
    weather_provider = OpenMeteoWeatherProvider()
    start = _resolve_location(origin, origin_lat, origin_lon, geocoder)
    end = _resolve_location(destination, destination_lat, destination_lon, geocoder)
    candidates = routing.routes(start, end, limit=3)
    if not candidates:
        raise RoutingError("No drivable routes were returned")

    points: list[GeoPoint] = []
    for candidate in candidates:
        points.extend(_corridor_points(candidate, sample_interval_miles))

    # Provider deduplicates rounded coordinates and batches requests; cache hits make
    # repeated slider sessions inexpensive.
    forecasts, _errors = weather_provider.forecasts(points)
    point_rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for point in points:
        key = weather_provider._coordinate_key(point)
        if key in seen:
            continue
        seen.add(key)
        point_rows.append(
            {
                "point": point,
                "key": key,
                "forecast": forecasts.get(key),
            }
        )

    frames: list[dict[str, Any]] = []
    partial_failure = False
    for hour_offset in FRAME_HOURS:
        timestamp = departure_time + timedelta(hours=hour_offset)
        features: list[dict[str, Any]] = []
        for row in point_rows:
            point: GeoPoint = row["point"]
            forecast = row["forecast"]
            properties: dict[str, Any] = {
                "hour_offset": hour_offset,
                "intensity": int(RiskLevel.SEVERE),
                "risk_level": "UNKNOWN",
                "wind_mph": None,
                "rain_in_hr": None,
                "snow_in_hr": None,
                "weather_status": "unavailable",
            }
            if forecast:
                try:
                    weather = weather_provider.at_time(forecast, timestamp)
                    assessment = assess_weather(
                        weather["wind_mph"],
                        weather["rain_in_hr"],
                        weather["snow_in_hr"],
                        load_weight_lb,
                    )
                    properties.update(
                        {
                            "intensity": int(assessment.level),
                            "risk_level": assessment.level.name,
                            "wind_mph": round(weather["wind_mph"], 2),
                            "rain_in_hr": round(weather["rain_in_hr"], 4),
                            "snow_in_hr": round(weather["snow_in_hr"], 4),
                            "weather_status": "ok",
                            "extrapolated": weather["extrapolated"],
                        }
                    )
                except (KeyError, TypeError, ValueError, WeatherProviderError):
                    partial_failure = True
            else:
                partial_failure = True
            features.append(
                {
                    "type": "Feature",
                    "properties": properties,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [round(point.lon, 4), round(point.lat, 4)],
                    },
                }
            )
        frames.append(
            {
                "hour_offset": hour_offset,
                "timestamp": timestamp.isoformat(),
                "geojson": {"type": "FeatureCollection", "features": features},
            }
        )

    return {
        "departure_time": departure_time.isoformat(),
        "frame_count": len(frames),
        "sample_count": len(point_rows),
        "route_count": len(candidates),
        "weather_partial_failure": partial_failure,
        "frames": frames,
    }
