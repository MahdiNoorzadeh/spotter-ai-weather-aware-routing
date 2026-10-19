from api.geometry import point_at_distance


def test_point_at_distance_returns_first_coordinate_at_origin():
    point = point_at_distance([[-122.0, 37.0], [-121.9, 37.0]], 0)
    assert point.lon == -122.0
    assert point.lat == 37.0


def test_analysis_returns_checkpoint_eta_weather_and_recommendation(monkeypatch):
    from datetime import datetime, timedelta

    from api.analysis import analyze_routes
    from api.providers.base import GeoPoint, RouteCandidate

    class FakeGeocoder:
        def search(self, query, limit=5):
            return [type("Suggestion", (), {"point": GeoPoint(37.0, -122.0)})()]

    class FakeRouting:
        def routes(self, origin, destination, limit=3):
            return [
                RouteCandidate(
                    route_id="route-1",
                    geometry={
                        "type": "LineString",
                        "coordinates": [[-122.0, 37.0], [-121.8, 37.0]],
                    },
                    distance_mi=20.0,
                    duration_seconds=7200.0,
                    provider="test",
                )
            ]

    class FakeWeather:
        @staticmethod
        def _coordinate_key(point):
            return "weather-key"

        def forecasts(self, points):
            return {
                "weather-key": {
                    "hourly": [
                        {
                            "time": "2026-10-19T10:00:00+00:00",
                            "wind_mph": 10.0,
                            "rain_in_hr": 0.0,
                            "snow_in_hr": 0.0,
                        }
                    ]
                }
            }, {}

        @staticmethod
        def at_time(forecast, eta):
            return {
                "wind_mph": 10.0,
                "rain_in_hr": 0.0,
                "snow_in_hr": 0.0,
                "forecast_time": "2026-10-19T10:00:00+00:00",
                "extrapolated": False,
            }

    monkeypatch.setattr("api.analysis.NominatimGeocodingProvider", FakeGeocoder)
    monkeypatch.setattr("api.analysis.FallbackRoutingProvider", FakeRouting)
    monkeypatch.setattr("api.analysis.OpenMeteoWeatherProvider", FakeWeather)
    departure = datetime.fromisoformat("2026-10-19T10:00:00+00:00")
    result = analyze_routes(
        {
            "origin": "origin",
            "destination": "destination",
            "departure_time": departure,
            "load_weight_lb": 10000,
        }
    )
    route = result["routes"][0]
    assert route["checkpoints"][0]["eta"] == departure.isoformat()
    assert route["checkpoints"][-1]["eta"] == (departure + timedelta(hours=2)).isoformat()
    assert route["checkpoints"][0]["final_level"] == "LOW"
    assert result["recommended_route_id"] == "route-1"
    assert result["route_count"] == 1
