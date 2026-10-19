"""Pure checkpoint sampling, segment mileage attribution, and ETA interpolation."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite

ALLOWED_INTERVALS_MILES = (10, 25, 50)


@dataclass(frozen=True)
class DurationPoint:
    """Cumulative route duration at a distance along the route."""

    mile_marker: float
    elapsed_seconds: float


def _validate_nonnegative(value: float, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite, non-negative number") from exc
    if not isfinite(number) or number < 0:
        raise ValueError(f"{name} must be a finite, non-negative number")
    return number


def adaptive_interval(distance_mi: float) -> int:
    distance = _validate_nonnegative(distance_mi, "distance_mi")
    if distance < 150:
        return 10
    if distance <= 500:
        return 25
    return 50


def sample_mile_markers(distance_mi: float, interval_miles: int | None = None) -> list[float]:
    """Return sorted checkpoint mile markers, always including 0 and destination."""
    distance = _validate_nonnegative(distance_mi, "distance_mi")
    interval = adaptive_interval(distance) if interval_miles is None else interval_miles
    if interval not in ALLOWED_INTERVALS_MILES:
        raise ValueError(f"interval_miles must be one of {ALLOWED_INTERVALS_MILES}")
    if distance == 0:
        return [0.0]

    markers = [0.0]
    mile = float(interval)
    while mile < distance:
        markers.append(mile)
        mile += interval
    if markers[-1] != distance:
        markers.append(distance)
    return markers


def segment_miles(mile_markers: Sequence[float], total_distance_mi: float) -> list[float]:
    """Assign each checkpoint its midpoint-bounded road segment.

    First segment starts at mile 0; last segment ends at total route distance.
    Each checkpoint owns the interval between midpoints to adjacent checkpoints.
    """
    total = _validate_nonnegative(total_distance_mi, "total_distance_mi")
    if not mile_markers:
        raise ValueError("mile_markers must include at least the origin")
    markers = [float(m) for m in mile_markers]
    if any(not isfinite(m) for m in markers):
        raise ValueError("mile markers must be finite")
    if any(m < 0 or m > total for m in markers):
        raise ValueError("mile markers must be within the route distance")
    if markers != sorted(markers) or len(set(markers)) != len(markers):
        raise ValueError("mile_markers must be strictly increasing")
    if abs(markers[0]) > 1e-9 or abs(markers[-1] - total) > 1e-9:
        if total == 0 and markers == [0.0]:
            return [0.0]
        raise ValueError("mile_markers must include origin 0 and destination total_distance_mi")

    boundaries = [0.0]
    boundaries.extend((markers[i] + markers[i + 1]) / 2 for i in range(len(markers) - 1))
    boundaries.append(total)
    return [max(0.0, boundaries[i + 1] - boundaries[i]) for i in range(len(markers))]


def _validate_aware_datetime(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("departure_time must be timezone-aware")


def elapsed_seconds_at_distance(
    mile_marker: float,
    total_distance_mi: float,
    total_duration_seconds: float,
    duration_profile: Sequence[DurationPoint] | None = None,
) -> float:
    """Interpolate cumulative duration; use profile points when supplied.

    Profile values are cumulative seconds from route start. Values outside the
    profile's range are clamped to its endpoints.
    """
    mile = _validate_nonnegative(mile_marker, "mile_marker")
    distance = _validate_nonnegative(total_distance_mi, "total_distance_mi")
    duration = _validate_nonnegative(total_duration_seconds, "total_duration_seconds")
    if mile > distance:
        raise ValueError("mile_marker cannot exceed total_distance_mi")
    if distance == 0:
        return 0.0

    if duration_profile:
        profile = sorted(duration_profile, key=lambda point: point.mile_marker)
        if any(p.mile_marker < 0 or p.mile_marker > distance for p in profile):
            raise ValueError("duration profile mile markers must be within route bounds")
        if any(not isfinite(p.elapsed_seconds) or p.elapsed_seconds < 0 for p in profile):
            raise ValueError("profile elapsed seconds must be finite and non-negative")
        points = list(profile)
        if not points or points[0].mile_marker > 0:
            points.insert(0, DurationPoint(0.0, 0.0))
        if points[-1].mile_marker < distance:
            points.append(DurationPoint(distance, duration))
        if any(points[i].mile_marker == points[i - 1].mile_marker for i in range(1, len(points))):
            raise ValueError("duration profile mile markers must be unique")
        for left, right in zip(points, points[1:], strict=False):
            if left.mile_marker <= mile <= right.mile_marker:
                fraction = (mile - left.mile_marker) / (right.mile_marker - left.mile_marker)
                return left.elapsed_seconds + fraction * (
                    right.elapsed_seconds - left.elapsed_seconds
                )
        return points[-1].elapsed_seconds

    return duration * mile / distance


def eta_at_distance(
    departure_time: datetime,
    mile_marker: float,
    total_distance_mi: float,
    total_duration_seconds: float,
    duration_profile: Sequence[DurationPoint] | None = None,
) -> datetime:
    _validate_aware_datetime(departure_time)
    seconds = elapsed_seconds_at_distance(
        mile_marker, total_distance_mi, total_duration_seconds, duration_profile
    )
    return departure_time + timedelta(seconds=seconds)


def checkpoint_etas(
    departure_time: datetime,
    mile_markers: Iterable[float],
    total_distance_mi: float,
    total_duration_seconds: float,
    duration_profile: Sequence[DurationPoint] | None = None,
) -> list[datetime]:
    return [
        eta_at_distance(
            departure_time, mile, total_distance_mi, total_duration_seconds, duration_profile
        )
        for mile in mile_markers
    ]
