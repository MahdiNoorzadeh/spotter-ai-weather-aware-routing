from datetime import UTC, datetime

from api.providers.weather import OpenMeteoWeatherProvider


def test_open_meteo_converts_units_and_selects_nearest_hour():
    row = {
        "hourly": {
            "time": ["2026-10-19T10:00", "2026-10-19T11:00"],
            "wind_speed_10m": [25.0, 30.0],
            "precipitation": [2.54, 5.08],
            "rain": [2.54, 5.08],
            "snowfall": [2.54, 5.08],
        }
    }
    normalized = OpenMeteoWeatherProvider._normalize_forecast(row)
    assert normalized is not None
    selected = OpenMeteoWeatherProvider.at_time(
        normalized, datetime(2026, 10, 19, 10, 40, tzinfo=UTC)
    )
    assert selected["wind_mph"] == 30.0
    assert selected["rain_in_hr"] == 0.2
    assert selected["snow_in_hr"] == 2.0
    assert selected["extrapolated"] is False


def test_open_meteo_clamps_eta_after_forecast_horizon_and_flags_it():
    forecast = {
        "hourly": [
            {
                "time": "2026-10-19T10:00:00+00:00",
                "wind_mph": 10.0,
                "rain_in_hr": 0.0,
                "snow_in_hr": 0.0,
            }
        ]
    }
    selected = OpenMeteoWeatherProvider.at_time(forecast, datetime(2026, 10, 20, 10, tzinfo=UTC))
    assert selected["forecast_time"] == "2026-10-19T10:00:00+00:00"
    assert selected["extrapolated"] is True


def test_forecasts_batches_unique_rounded_coordinates_and_caches(monkeypatch, settings):
    from django.core.cache import cache

    from api.providers.base import GeoPoint

    cache.clear()
    calls = []

    def fake_get_json(url, *, params=None, headers=None):
        calls.append(params)
        rows = []
        for _lat in params["latitude"].split(","):
            rows.append(
                {
                    "hourly": {
                        "time": ["2026-10-19T10:00"],
                        "wind_speed_10m": [12],
                        "precipitation": [0],
                        "rain": [0],
                        "snowfall": [0],
                    }
                }
            )
        return rows if len(rows) > 1 else rows[0]

    monkeypatch.setattr("api.providers.weather.get_json", fake_get_json)
    provider = OpenMeteoWeatherProvider()
    points = [GeoPoint(52.52001, 13.40501), GeoPoint(52.52002, 13.40502)]
    forecasts, errors = provider.forecasts(points)
    assert not errors
    assert len(forecasts) == 1
    assert len(calls) == 1
    assert calls[0]["wind_speed_unit"] == "mph"
