"""Orchestrates route candidates, ETA-aware checkpoint weather, and ranking."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from api.errors import GeocodingError, RoutingError
from api.geometry import point_at_distance
from api.providers.base import GeoPoint, RouteCandidate
from api.providers.geocoding import NominatimGeocodingProvider
from api.providers.routing import FallbackRoutingProvider
from api.providers.weather import OpenMeteoWeatherProvider
from routing.recommend import (
    RiskSegment,
    RouteMetrics,
    rank_routes,
    recommendation_reason,
    summarize_route,
)
from routing.risk import RiskLevel, assess_weather
from routing.sampling import (
    DurationPoint,
    adaptive_interval,
    elapsed_seconds_at_distance,
    sample_mile_markers,
    segment_miles,
)


def _resolve_location(
    value: str | None,
    point_value: dict | None,
    geocoder: NominatimGeocodingProvider,
) -> GeoPoint:
    if point_value:
        return GeoPoint(
            float(point_value["lat"]),
            float(point_value["lon"]),
            point_value.get("label", ""),
        )
    assert value is not None
    suggestions = geocoder.search(value, limit=1)
    if not suggestions:
        raise GeocodingError(f"Could not find a location matching '{value}'")
    return suggestions[0].point


def analyze_routes(data: dict[str, Any]) -> dict[str, Any]:
    geocoder = NominatimGeocodingProvider()
    routing = FallbackRoutingProvider()
    weather_provider = OpenMeteoWeatherProvider()
    origin = _resolve_location(data.get("origin"), data.get("origin_point"), geocoder)
    destination = _resolve_location(
        data.get("destination"), data.get("destination_point"), geocoder
    )
    candidates = routing.routes(origin, destination, limit=3)
    if not candidates:
        raise RoutingError("No drivable routes were returned")

    departure: datetime = data["departure_time"]
    load_weight = float(data["load_weight_lb"])
    prepared: list[dict[str, Any]] = []
    weather_points: list[GeoPoint] = []

    for candidate in candidates:
        interval = data.get("interval_miles") or adaptive_interval(candidate.distance_mi)
        markers = sample_mile_markers(candidate.distance_mi, interval)
        geometry = candidate.geometry
        coordinates = geometry["coordinates"]
        points = [point_at_distance(coordinates, marker) for marker in markers]
        profile = [DurationPoint(mile, seconds) for mile, seconds in candidate.duration_profile]
        checkpoint_rows = []
        for marker, point in zip(markers, points, strict=True):
            elapsed = elapsed_seconds_at_distance(
                marker, candidate.distance_mi, candidate.duration_seconds, profile or None
            )
            eta = departure + timedelta(seconds=elapsed)
            checkpoint = {
                "lat": round(point.lat, 6),
                "lon": round(point.lon, 6),
                "mile_marker": round(marker, 3),
                "eta": eta.isoformat(),
                "_eta": eta,
                "_point": point,
            }
            checkpoint_rows.append(checkpoint)
            weather_points.append(point)
        prepared.append(
            {
                "candidate": candidate,
                "interval": interval,
                "markers": markers,
                "points": points,
                "checkpoints": checkpoint_rows,
            }
        )

    forecasts, weather_errors = weather_provider.forecasts(weather_points)
    ranked_metrics: list[RouteMetrics] = []
    route_payloads: list[dict[str, Any]] = []
    for item in prepared:
        candidate: RouteCandidate = item["candidate"]
        checkpoints = item["checkpoints"]
        owned_miles = segment_miles(item["markers"], candidate.distance_mi)
        risk_segments: list[RiskSegment] = []
        unknown_miles = 0.0
        serialized_checkpoints: list[dict[str, Any]] = []
        for checkpoint, miles in zip(checkpoints, owned_miles, strict=True):
            point: GeoPoint = checkpoint["_point"]
            key = weather_provider._coordinate_key(point)
            forecast = forecasts.get(key)
            weather_error = weather_errors.get(key)
            if forecast:
                try:
                    weather = weather_provider.at_time(forecast, checkpoint["_eta"])
                    assessment = assess_weather(
                        weather["wind_mph"],
                        weather["rain_in_hr"],
                        weather["snow_in_hr"],
                        load_weight,
                    )
                    level = assessment.level
                    base_level = assessment.base_level
                    reasons = list(assessment.reasons)
                    serialized_checkpoints.append(
                        {
                            "lat": checkpoint["lat"],
                            "lon": checkpoint["lon"],
                            "mile_marker": checkpoint["mile_marker"],
                            "eta": checkpoint["eta"],
                            "weather": weather,
                            "base_level": base_level.name,
                            "final_level": level.name,
                            "reasons": reasons,
                            "weather_status": "ok",
                        }
                    )
                    risk_segments.append(RiskSegment(level, miles))
                except Exception:
                    weather_error = "Forecast data could not be interpreted for this checkpoint"
            if not forecast or weather_error:
                unknown_miles += miles
                # Conservative ranking: missing weather must never be treated as safe.
                risk_segments.append(RiskSegment(RiskLevel.SEVERE, miles))
                serialized_checkpoints.append(
                    {
                        "lat": checkpoint["lat"],
                        "lon": checkpoint["lon"],
                        "mile_marker": checkpoint["mile_marker"],
                        "eta": checkpoint["eta"],
                        "weather": None,
                        "base_level": None,
                        "final_level": "UNKNOWN",
                        "reasons": [
                            weather_error or "Weather forecast unavailable; risk is unknown"
                        ],
                        "weather_status": "unavailable",
                    }
                )
        metrics = RouteMetrics(
            candidate.route_id,
            candidate.distance_mi,
            candidate.duration_seconds / 60,
            tuple(risk_segments),
        )
        ranked_metrics.append(metrics)
        summary = summarize_route(metrics)
        route_payloads.append(
            {
                "id": candidate.route_id,
                "provider": candidate.provider,
                "geometry": candidate.geometry,
                "distance_mi": round(candidate.distance_mi, 2),
                "duration_min": round(candidate.duration_seconds / 60, 1),
                "eta_destination": serialized_checkpoints[-1]["eta"],
                "interval_miles": item["interval"],
                "checkpoints": serialized_checkpoints,
                "summary": {
                    "severe_miles": round(summary.severe_miles, 2),
                    "high_miles": round(summary.high_miles, 2),
                    "moderate_miles": round(summary.moderate_miles, 2),
                    "low_miles": round(summary.low_miles, 2),
                    "no_travel_miles": round(summary.no_travel_miles, 2),
                    "unknown_miles": round(unknown_miles, 2),
                    "avg_risk": round(summary.avg_risk, 3),
                    "total_time_min": round(summary.total_time_min, 1),
                    "distance_mi": round(summary.distance_mi, 2),
                },
            }
        )

    ranked = rank_routes(ranked_metrics)
    winner = ranked[0]
    all_no_travel = all(summarize_route(route).no_travel_miles > 0 for route in ranked)
    return {
        "routes": route_payloads,
        "recommended_route_id": winner.route_id,
        "recommendation_reason": recommendation_reason(ranked, winner),
        "no_safe_route": all_no_travel,
        "route_count": len(route_payloads),
        "routes_notice": (
            None
            if len(route_payloads) >= 3
            else f"Only {len(route_payloads)} distinct route(s) were available "
            "for this origin and destination."
        ),
        "weather_partial_failure": any(
            route["summary"]["unknown_miles"] > 0 for route in route_payloads
        ),
        "ranking_order": [route.route_id for route in ranked],
    }
