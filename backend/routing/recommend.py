"""Pure route ranking and mileage-weighted risk summaries."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from math import isfinite

from .risk import RiskLevel, risk_score


@dataclass(frozen=True)
class RiskSegment:
    """Risk level assigned to a road segment of a given length."""

    level: RiskLevel
    miles: float


@dataclass(frozen=True)
class RouteMetrics:
    """Metrics required to compare route candidates."""

    route_id: str
    distance_mi: float
    duration_min: float
    segments: tuple[RiskSegment, ...]

    def __post_init__(self) -> None:
        if not self.route_id:
            raise ValueError("route_id must not be empty")
        for name, value in (
            ("distance_mi", self.distance_mi),
            ("duration_min", self.duration_min),
        ):
            if not isfinite(float(value)) or float(value) < 0:
                raise ValueError(f"{name} must be finite and non-negative")
        if any(not isfinite(float(s.miles)) or s.miles < 0 for s in self.segments):
            raise ValueError("segment miles must be finite and non-negative")


@dataclass(frozen=True)
class RouteSummary:
    route_id: str
    severe_miles: float
    high_miles: float
    moderate_miles: float
    no_travel_miles: float
    low_miles: float
    avg_risk: float
    total_time_min: float
    distance_mi: float


def summarize_route(route: RouteMetrics) -> RouteSummary:
    totals = {level: 0.0 for level in RiskLevel}
    weighted_score = 0.0
    total_segment_miles = 0.0

    for segment in route.segments:
        miles = float(segment.miles)
        level = RiskLevel(segment.level)
        totals[level] += miles
        weighted_score += risk_score(level) * miles
        total_segment_miles += miles

    avg_risk = weighted_score / total_segment_miles if total_segment_miles > 0 else 0.0
    return RouteSummary(
        route_id=route.route_id,
        severe_miles=totals[RiskLevel.SEVERE],
        high_miles=totals[RiskLevel.HIGH],
        moderate_miles=totals[RiskLevel.MODERATE],
        no_travel_miles=totals[RiskLevel.NO_TRAVEL],
        low_miles=totals[RiskLevel.LOW],
        avg_risk=avg_risk,
        total_time_min=float(route.duration_min),
        distance_mi=float(route.distance_mi),
    )


def ranking_key(route: RouteMetrics) -> tuple[float, ...]:
    """Smaller tuple wins; No Travel is a hard disqualifier.

    Routes without No Travel rank above every route containing it. When all
    candidates contain No Travel, minimize No Travel miles before the four
    standard criteria. The standard criteria are Severe miles, High miles,
    mileage-weighted average risk, then duration.
    """
    summary = summarize_route(route)
    has_no_travel = summary.no_travel_miles > 0
    return (
        1.0 if has_no_travel else 0.0,
        summary.no_travel_miles if has_no_travel else 0.0,
        summary.severe_miles,
        summary.high_miles,
        summary.avg_risk,
        summary.total_time_min,
    )


def recommend_route(routes: Sequence[RouteMetrics]) -> RouteMetrics:
    if not routes:
        raise ValueError("At least one route is required")
    return min(routes, key=ranking_key)


def rank_routes(routes: Iterable[RouteMetrics]) -> list[RouteMetrics]:
    return sorted(routes, key=ranking_key)


def recommendation_reason(routes: Sequence[RouteMetrics], winner: RouteMetrics) -> str:
    if not routes:
        raise ValueError("At least one route is required")
    summaries = {route.route_id: summarize_route(route) for route in routes}
    selected = summaries[winner.route_id]
    all_have_no_travel = all(s.no_travel_miles > 0 for s in summaries.values())

    if all_have_no_travel:
        return (
            f"No safe route at this departure time. {winner.route_id} is the "
            f"least-bad option with {selected.no_travel_miles:.1f} No Travel miles."
        )
    if selected.no_travel_miles == 0:
        return (
            f"{winner.route_id} is recommended: it has no No Travel miles, "
            f"{selected.severe_miles:.1f} Severe miles, "
            f"{selected.high_miles:.1f} High miles, and takes "
            f"{selected.total_time_min:.0f} minutes."
        )
    return (
        f"{winner.route_id} is the least-bad available option, with "
        f"{selected.no_travel_miles:.1f} No Travel miles."
    )
