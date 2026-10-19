"""Provider contracts and shared transport-neutral data types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GeoPoint:
    lat: float
    lon: float
    label: str = ""


@dataclass(frozen=True)
class GeocodeSuggestion:
    point: GeoPoint
    place_name: str
    provider_id: str | None = None


@dataclass(frozen=True)
class RouteCandidate:
    route_id: str
    geometry: dict[str, object]
    distance_mi: float
    duration_seconds: float
    # Each item is (cumulative distance in miles, cumulative elapsed seconds).
    duration_profile: tuple[tuple[float, float], ...] = ()
    provider: str = "unknown"


class GeocodingProvider(Protocol):
    def search(self, query: str, limit: int = 5) -> list[GeocodeSuggestion]: ...


class RoutingProvider(Protocol):
    def routes(
        self, origin: GeoPoint, destination: GeoPoint, limit: int = 3
    ) -> list[RouteCandidate]: ...
