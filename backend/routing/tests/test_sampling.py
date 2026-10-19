from datetime import UTC, datetime, timedelta

import pytest

from routing.sampling import (
    DurationPoint,
    adaptive_interval,
    checkpoint_etas,
    elapsed_seconds_at_distance,
    eta_at_distance,
    sample_mile_markers,
    segment_miles,
)


def test_adaptive_interval_boundaries():
    assert adaptive_interval(149.99) == 10
    assert adaptive_interval(150) == 25
    assert adaptive_interval(500) == 25
    assert adaptive_interval(500.01) == 50


@pytest.mark.parametrize(
    ("distance", "interval", "expected"),
    [
        (0, 10, [0.0]),
        (8, 10, [0.0, 8.0]),
        (25, 10, [0.0, 10.0, 20.0, 25.0]),
        (50, 25, [0.0, 25.0, 50.0]),
    ],
)
def test_sample_markers_include_origin_and_destination(distance, interval, expected):
    assert sample_mile_markers(distance, interval) == expected


def test_sample_markers_rejects_invalid_interval():
    with pytest.raises(ValueError):
        sample_mile_markers(100, 15)


def test_midpoint_mileage_attribution():
    assert segment_miles([0, 10, 20], 20) == [5.0, 10.0, 5.0]


def test_midpoint_mileage_attribution_uneven_checkpoints():
    assert segment_miles([0, 10, 25], 25) == [5.0, 12.5, 7.5]


def test_single_zero_distance_checkpoint():
    assert segment_miles([0], 0) == [0.0]


def test_segment_miles_requires_endpoints():
    with pytest.raises(ValueError):
        segment_miles([0, 10], 20)


def test_eta_linear_interpolation():
    departure = datetime(2026, 1, 1, 8, tzinfo=UTC)
    eta = eta_at_distance(departure, 25, 100, 4 * 3600)
    assert eta == departure + timedelta(hours=1)


def test_eta_uses_duration_profile_when_provided():
    departure = datetime(2026, 1, 1, 8, tzinfo=UTC)
    profile = [DurationPoint(0, 0), DurationPoint(20, 3600), DurationPoint(100, 7200)]
    eta = eta_at_distance(departure, 60, 100, 7200, profile)
    assert eta == departure + timedelta(seconds=5400)


def test_eta_requires_timezone_aware_departure():
    with pytest.raises(ValueError):
        eta_at_distance(datetime(2026, 1, 1, 8), 0, 100, 3600)


def test_checkpoint_etas_preserve_order_and_end_at_total_duration():
    departure = datetime(2026, 1, 1, 8, tzinfo=UTC)
    values = checkpoint_etas(departure, [0, 50, 100], 100, 7200)
    assert values == [
        departure,
        departure + timedelta(hours=1),
        departure + timedelta(hours=2),
    ]


def test_distance_cannot_exceed_route_length():
    with pytest.raises(ValueError):
        elapsed_seconds_at_distance(101, 100, 3600)
