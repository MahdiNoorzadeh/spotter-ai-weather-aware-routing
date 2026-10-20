"""Mapbox Directions with an OSRM public-service fallback."""

from __future__ import annotations

from math import isfinite

from django.conf import settings
from django.core.cache import cache

from api.errors import RoutingError
from api.providers.base import GeoPoint, RouteCandidate
from api.providers.http import cache_key, get_json

METERS_PER_MILE = 1609.344


def _route_candidate(route: dict, route_id: str, provider: str) -> RouteCandidate:
    geometry = route.get("geometry")
    if isinstance(geometry, dict) and geometry.get("type") == "LineString":
        coordinates = geometry.get("coordinates")
    else:
        raise RoutingError("Routing provider returned invalid route geometry")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        raise RoutingError("Routing provider returned an empty route geometry")
    try:
        distance_mi = float(route["distance"]) / METERS_PER_MILE
        duration_seconds = float(route["duration"])
    except (KeyError, TypeError, ValueError) as exc:
        raise RoutingError("Routing provider omitted route distance or duration") from exc
    if (
        not isfinite(distance_mi)
        or distance_mi <= 0
        or not isfinite(duration_seconds)
        or duration_seconds < 0
    ):
        raise RoutingError("Routing provider returned invalid distance or duration")

    profile: list[tuple[float, float]] = [(0.0, 0.0)]
    cumulative_distance = 0.0
    cumulative_duration = 0.0
    legs = route.get("legs", [])
    for leg in legs if isinstance(legs, list) else []:
        steps = leg.get("steps", []) if isinstance(leg, dict) else []
        for step in steps if isinstance(steps, list) else []:
            if not isinstance(step, dict):
                continue
            try:
                cumulative_distance += max(0.0, float(step.get("distance", 0))) / METERS_PER_MILE
                cumulative_duration += max(0.0, float(step.get("duration", 0)))
            except (TypeError, ValueError):
                continue
            profile.append(
                (
                    min(cumulative_distance, distance_mi),
                    min(cumulative_duration, duration_seconds),
                )
            )
    profile.append((distance_mi, duration_seconds))
    # Collapse duplicate distance points; sampling interpolation requires unique markers.
    unique_profile: list[tuple[float, float]] = []
    for point in profile:
        if unique_profile and abs(point[0] - unique_profile[-1][0]) < 1e-7:
            unique_profile[-1] = point
        else:
            unique_profile.append(point)
    return RouteCandidate(
        route_id=route_id,
        geometry={"type": "LineString", "coordinates": coordinates},
        distance_mi=distance_mi,
        duration_seconds=duration_seconds,
        duration_profile=tuple(unique_profile),
        provider=provider,
    )


class OsrmRoutingProvider:
    base_url = "https://router.project-osrm.org/route/v1/driving"

    def routes(
        self, origin: GeoPoint, destination: GeoPoint, limit: int = 3
    ) -> list[RouteCandidate]:
        coords = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
        key = cache_key("routes:osrm", {"coords": coords, "limit": limit})
        cached = cache.get(key)
        if cached is not None:
            return [self._from_cache(row) for row in cached]
        try:
            payload = get_json(
                f"{self.base_url}/{coords}",
                params={
                    "alternatives": min(max(limit, 1), 3),
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "true",
                },
            )
            if payload.get("code") != "Ok" or not isinstance(payload.get("routes"), list):
                raise RoutingError("OSRM could not find a drivable route for these locations")
            routes = [
                _route_candidate(row, f"route-{index + 1}", "osrm")
                for index, row in enumerate(payload["routes"][:limit])
            ]
            cache.set(
                key,
                [self._to_cache(route) for route in routes],
                settings.ROUTE_CACHE_SECONDS,
            )
            return routes
        except RoutingError:
            raise
        except (RuntimeError, AttributeError, TypeError, ValueError) as exc:
            raise RoutingError("Routing service is temporarily unavailable") from exc

    @staticmethod
    def _to_cache(route: RouteCandidate) -> dict:
        return {
            "route_id": route.route_id,
            "geometry": route.geometry,
            "distance_mi": route.distance_mi,
            "duration_seconds": route.duration_seconds,
            "duration_profile": route.duration_profile,
            "provider": route.provider,
        }

    @staticmethod
    def _from_cache(row: dict) -> RouteCandidate:
        return RouteCandidate(
            row["route_id"],
            row["geometry"],
            row["distance_mi"],
            row["duration_seconds"],
            tuple(tuple(point) for point in row["duration_profile"]),
            row["provider"],
        )


class MapboxRoutingProvider:
    base_url = "https://api.mapbox.com/directions/v5/mapbox/driving"

    def routes(
        self, origin: GeoPoint, destination: GeoPoint, limit: int = 3
    ) -> list[RouteCandidate]:
        token = settings.MAPBOX_ACCESS_TOKEN
        if not token:
            raise RoutingError("Mapbox access token is not configured")
        coords = f"{origin.lon},{origin.lat};{destination.lon},{destination.lat}"
        key = cache_key("routes:mapbox", {"coords": coords, "limit": limit})
        cached = cache.get(key)
        if cached is not None:
            return [OsrmRoutingProvider._from_cache(row) for row in cached]
        try:
            payload = get_json(
                f"{self.base_url}/{coords}",
                params={
                    "access_token": token,
                    "alternatives": "true",
                    "overview": "full",
                    "geometries": "geojson",
                    "steps": "true",
                    "language": "en",
                },
            )
            if payload.get("code") != "Ok" or not isinstance(payload.get("routes"), list):
                raise RoutingError("Mapbox could not find a drivable route for these locations")
            routes = [
                _route_candidate(row, f"route-{index + 1}", "mapbox")
                for index, row in enumerate(payload["routes"][:limit])
            ]
            cache.set(
                key,
                [OsrmRoutingProvider._to_cache(route) for route in routes],
                settings.ROUTE_CACHE_SECONDS,
            )
            return routes
        except RoutingError:
            raise
        except (RuntimeError, AttributeError, TypeError, ValueError) as exc:
            raise RoutingError("Mapbox routing service is temporarily unavailable") from exc


class FallbackRoutingProvider:
    """Prefer Mapbox when configured, then fall back to the free OSRM endpoint."""

    def __init__(self) -> None:
        self.mapbox = MapboxRoutingProvider()
        self.osrm = OsrmRoutingProvider()

    def routes(
        self, origin: GeoPoint, destination: GeoPoint, limit: int = 3
    ) -> list[RouteCandidate]:
        mapbox_routes: list[RouteCandidate] = []
        if settings.MAPBOX_ACCESS_TOKEN:
            try:
                mapbox_routes = self.mapbox.routes(origin, destination, limit)
            except RoutingError:
                mapbox_routes = []
        if len(mapbox_routes) >= limit:
            return [
                self._renumber(route, index)
                for index, route in enumerate(mapbox_routes[:limit], start=1)
            ]
        try:
            osrm_routes = self.osrm.routes(origin, destination, limit)
        except RoutingError:
            if mapbox_routes:
                return [
                    self._renumber(route, index)
                    for index, route in enumerate(mapbox_routes, start=1)
                ]
            raise

        combined: list[RouteCandidate] = []
        signatures: set[tuple[tuple[float, float], ...]] = set()
        for route in [*mapbox_routes, *osrm_routes]:
            coordinates = route.geometry.get("coordinates", [])
            signature = tuple(
                (round(float(point[0]), 4), round(float(point[1]), 4))
                for point in coordinates[:: max(1, len(coordinates) // 20)]
            )
            if signature in signatures:
                continue
            signatures.add(signature)
            combined.append(route)
            if len(combined) >= limit:
                break
        return [self._renumber(route, index) for index, route in enumerate(combined, start=1)]

    @staticmethod
    def _renumber(route: RouteCandidate, index: int) -> RouteCandidate:
        return RouteCandidate(
            route_id=f"route-{index}",
            geometry=route.geometry,
            distance_mi=route.distance_mi,
            duration_seconds=route.duration_seconds,
            duration_profile=route.duration_profile,
            provider=route.provider,
        )
