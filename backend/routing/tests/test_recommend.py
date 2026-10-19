import pytest

from routing.recommend import (
    RiskSegment,
    RouteMetrics,
    rank_routes,
    recommend_route,
    recommendation_reason,
    summarize_route,
)
from routing.risk import RiskLevel as R


def route(route_id, segments, duration=100, distance=100):
    return RouteMetrics(
        route_id=route_id,
        distance_mi=distance,
        duration_min=duration,
        segments=tuple(RiskSegment(level, miles) for level, miles in segments),
    )


def test_average_risk_is_mileage_weighted():
    item = route("A", [(R.LOW, 90), (R.SEVERE, 10)])
    assert summarize_route(item).avg_risk == pytest.approx(0.3)


def test_no_travel_free_route_beats_shorter_route_with_no_travel():
    unsafe_but_short = route("A", [(R.NO_TRAVEL, 1), (R.LOW, 99)], duration=50)
    safe_but_long = route("B", [(R.LOW, 100)], duration=120)
    assert recommend_route([unsafe_but_short, safe_but_long]).route_id == "B"


def test_fewest_no_travel_miles_first_when_all_routes_have_them():
    more_no_travel = route("A", [(R.NO_TRAVEL, 10), (R.LOW, 90)])
    less_no_travel = route("B", [(R.NO_TRAVEL, 5), (R.SEVERE, 95)])
    assert recommend_route([more_no_travel, less_no_travel]).route_id == "B"


def test_severe_miles_precede_high_miles():
    fewer_severe = route("A", [(R.SEVERE, 1), (R.HIGH, 50), (R.LOW, 49)])
    more_severe = route("B", [(R.SEVERE, 2), (R.LOW, 98)])
    assert recommend_route([more_severe, fewer_severe]).route_id == "A"


def test_high_miles_precede_average_risk():
    fewer_high = route("A", [(R.HIGH, 1), (R.MODERATE, 99)])
    more_high = route("B", [(R.HIGH, 2), (R.LOW, 98)])
    assert recommend_route([more_high, fewer_high]).route_id == "A"


def test_average_risk_precedes_duration():
    lower_average = route("A", [(R.MODERATE, 100)], duration=200)
    higher_average = route("B", [(R.HIGH, 1), (R.LOW, 99)], duration=10)
    assert recommend_route([higher_average, lower_average]).route_id == "A"


def test_duration_breaks_complete_risk_tie():
    slower = route("A", [(R.LOW, 100)], duration=101)
    faster = route("B", [(R.LOW, 100)], duration=100)
    assert recommend_route([slower, faster]).route_id == "B"


def test_no_routes_raises():
    with pytest.raises(ValueError):
        recommend_route([])


def test_all_routes_no_travel_reason_has_required_warning():
    a = route("A", [(R.NO_TRAVEL, 10), (R.LOW, 90)])
    b = route("B", [(R.NO_TRAVEL, 5), (R.LOW, 95)])
    winner = recommend_route([a, b])
    reason = recommendation_reason([a, b], winner)
    assert "No safe route at this departure time" in reason
    assert "B" in reason


def test_rank_routes_returns_best_first():
    a = route("A", [(R.SEVERE, 1), (R.LOW, 99)])
    b = route("B", [(R.LOW, 100)])
    assert [r.route_id for r in rank_routes([a, b])] == ["B", "A"]


def test_no_travel_miles_are_reported_in_summary():
    item = route("A", [(R.NO_TRAVEL, 7), (R.SEVERE, 3)])
    summary = summarize_route(item)
    assert summary.no_travel_miles == 7
    assert summary.severe_miles == 3
