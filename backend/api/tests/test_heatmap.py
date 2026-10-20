from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.test import override_settings
from rest_framework.test import APIClient

from api.providers.base import RouteCandidate


@pytest.fixture
def api_client():
    return APIClient()


def _candidate():
    return RouteCandidate(
        route_id="route-1",
        geometry={"type": "LineString", "coordinates": [[10.0, 53.0], [10.6, 53.4]]},
        distance_mi=40.0,
        duration_seconds=3600.0,
        provider="test",
    )


def _forecast():
    # A deterministic 49-hour forecast, with changing hourly wind values.
    from datetime import timedelta

    start = datetime(2026, 10, 21, 9, tzinfo=UTC)
    return {
        "hourly": [
            {
                "time": (start + timedelta(hours=hour)).isoformat(),
                "wind_mph": 10.0 + hour,
                "rain_in_hr": 0.0,
                "snow_in_hr": 0.0,
            }
            for hour in range(49)
        ]
    }


@override_settings(NOMINATIM_USER_AGENT="SpotterTest/1.0 (test@example.com)")
def test_heatmap_returns_49_frames_and_uses_shared_risk_logic(api_client):
    with (
        patch("api.heatmap.FallbackRoutingProvider.routes", return_value=[_candidate()]),
        patch("api.heatmap.OpenMeteoWeatherProvider.forecasts") as forecasts,
    ):
        def fake_forecasts(points):
            from api.providers.weather import OpenMeteoWeatherProvider

            provider = OpenMeteoWeatherProvider()
            return (
                {provider._coordinate_key(point): _forecast() for point in points},
                {},
            )

        forecasts.side_effect = fake_forecasts
        response = api_client.get(
            "/api/heatmap",
            {
                "origin_lat": "53.0",
                "origin_lon": "10.0",
                "destination_lat": "53.4",
                "destination_lon": "10.6",
                "departure_time": "2026-10-21T09:00:00+00:00",
                "load_weight_lb": "10000",
                "sample_interval_miles": "20",
            },
        )

    assert response.status_code == 200, response.content
    payload = response.json()
    assert payload["frame_count"] == 49
    assert [frame["hour_offset"] for frame in payload["frames"]] == list(range(49))
    assert payload["frames"][0]["timestamp"] == "2026-10-21T09:00:00+00:00"
    assert payload["frames"][-1]["timestamp"] == "2026-10-23T09:00:00+00:00"

    features = payload["frames"][0]["geojson"]["features"]
    assert features
    assert features[0]["geometry"]["type"] == "Point"
    assert features[0]["properties"]["risk_level"] == "LOW"
    assert features[0]["properties"]["intensity"] == 0
    assert (
        payload["frames"][24]["geojson"]["features"][0]["properties"]["risk_level"]
        == "MODERATE"
    )

    # The mocked wind forecast is 10 + hour_offset mph.
    # A 10,000 lb load does not trigger load overrides.
    expected_levels = [
        (0, "LOW", 0),          # 10 mph
        (15, "MODERATE", 1),    # 25 mph
        (25, "HIGH", 2),        # 35 mph
        (35, "SEVERE", 3),      # 45 mph
        (45, "NO_TRAVEL", 4),   # 55 mph
    ]

    for hour_offset, expected_level, expected_intensity in expected_levels:
        features = payload["frames"][hour_offset]["geojson"]["features"]
        assert features, f"No heatmap features at hour {hour_offset}"

        properties = features[0]["properties"]
        assert properties["risk_level"] == expected_level
        assert properties["intensity"] == expected_intensity


def test_heatmap_requires_timezone_and_valid_weight(api_client):
    response = api_client.get(
        "/api/heatmap",
        {
            "origin_lat": "53.0",
            "origin_lon": "10.0",
            "destination_lat": "53.4",
            "destination_lon": "10.6",
            "departure_time": "2026-10-21T09:00:00",
            "load_weight_lb": "200001",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_heatmap_rejects_partial_coordinate_pair(api_client):
    response = api_client.get(
        "/api/heatmap",
        {
            "origin_lat": "53.0",
            "destination_lat": "53.4",
            "destination_lon": "10.6",
            "departure_time": "2026-10-21T09:00:00+00:00",
            "load_weight_lb": "10000",
        },
    )
    assert response.status_code == 400
    assert "origin" in response.json()["error"]["details"]


def test_heatmap_weather_failure_marks_points_unknown(api_client):
    with (
        patch("api.heatmap.FallbackRoutingProvider.routes", return_value=[_candidate()]),
        patch(
            "api.heatmap.OpenMeteoWeatherProvider.forecasts",
            return_value=({}, {"x": "offline"}),
        ),
    ):
        response = api_client.get(
            "/api/heatmap",
            {
                "origin_lat": "53.0",
                "origin_lon": "10.0",
                "destination_lat": "53.4",
                "destination_lon": "10.6",
                "departure_time": "2026-10-21T09:00:00+00:00",
                "load_weight_lb": "10000",
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["weather_partial_failure"] is True
    feature = payload["frames"][0]["geojson"]["features"][0]
    assert feature["properties"]["risk_level"] == "UNKNOWN"
    assert feature["properties"]["weather_status"] == "unavailable"