"""Batched Open-Meteo forecast client with per-coordinate forecast caching."""

from __future__ import annotations

from datetime import UTC, datetime
from math import isfinite
from typing import Any

from django.conf import settings
from django.core.cache import cache

from api.errors import WeatherProviderError
from api.providers.base import GeoPoint
from api.providers.http import cache_key, get_json


class OpenMeteoWeatherProvider:
    base_url = "https://api.open-meteo.com/v1/forecast"
    batch_size = 50

    @staticmethod
    def _coordinate_key(point: GeoPoint) -> str:
        return cache_key(
            "weather:forecast",
            {
                "lat": round(point.lat, 3),
                "lon": round(point.lon, 3),
                "units": "mph-inches",
            },
        )

    def forecasts(self, points: list[GeoPoint]) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
        """Return forecast data keyed by rounded coordinate key, plus per-key errors.

        Coordinates are rounded before both caching and provider requests to reduce
        duplicate calls while preserving sufficient precision for route checkpoints.
        """
        unique: dict[str, GeoPoint] = {}
        for point in points:
            unique.setdefault(
                self._coordinate_key(point),
                GeoPoint(round(point.lat, 3), round(point.lon, 3), point.label),
            )
        forecasts: dict[str, dict[str, Any]] = {}
        errors: dict[str, str] = {}
        missing: list[tuple[str, GeoPoint]] = []
        for key, point in unique.items():
            cached = cache.get(key)
            if isinstance(cached, dict):
                forecasts[key] = cached
            else:
                missing.append((key, point))

        for start in range(0, len(missing), self.batch_size):
            batch = missing[start : start + self.batch_size]
            if not batch:
                continue
            params = {
                "latitude": ",".join(str(point.lat) for _, point in batch),
                "longitude": ",".join(str(point.lon) for _, point in batch),
                "hourly": "wind_speed_10m,precipitation,rain,snowfall",
                "wind_speed_unit": "mph",
                "precipitation_unit": "mm",
                "timezone": "GMT",
                "forecast_days": 7,
            }
            try:
                payload = get_json(self.base_url, params=params)
                # Open-Meteo returns a dict for one location and a list for multiple.
                rows = payload if isinstance(payload, list) else [payload]
                if len(batch) == 1 and len(rows) == 1:
                    pass
                elif len(rows) != len(batch):
                    raise WeatherProviderError(
                        "Weather provider returned a mismatched number of locations"
                    )
                for (key, _), row in zip(batch, rows, strict=True):
                    normalized = self._normalize_forecast(row)
                    if normalized is None:
                        errors[key] = "Weather response did not include usable hourly forecast data"
                        continue
                    forecasts[key] = normalized
                    cache.set(key, normalized, settings.WEATHER_CACHE_SECONDS)
            except (RuntimeError, WeatherProviderError, TypeError, ValueError):
                # Retry locations separately if the batched request fails.
                for key, point in batch:
                    try:
                        single_payload = get_json(
                            self.base_url,
                            params={
                                "latitude": str(point.lat),
                                "longitude": str(point.lon),
                                "hourly": "wind_speed_10m,precipitation,rain,snowfall",
                                "wind_speed_unit": "mph",
                                "precipitation_unit": "mm",
                                "timezone": "GMT",
                                "forecast_days": 7,
                            },
                        )
                        normalized = self._normalize_forecast(single_payload)
                        if normalized is None:
                            errors[key] = (
                                "Weather response did not include usable hourly forecast data"
                            )
                            continue
                        forecasts[key] = normalized
                        cache.set(key, normalized, settings.WEATHER_CACHE_SECONDS)
                    except (RuntimeError, WeatherProviderError, TypeError, ValueError):
                        errors[key] = "Weather service is temporarily unavailable"

        return forecasts, errors

    @staticmethod
    def _normalize_forecast(row: Any) -> dict[str, Any] | None:
        if not isinstance(row, dict):
            return None
        hourly = row.get("hourly")
        if not isinstance(hourly, dict):
            return None
        times = hourly.get("time")
        winds = hourly.get("wind_speed_10m")
        rains = hourly.get("rain")
        precip = hourly.get("precipitation")
        snows = hourly.get("snowfall")

        if not isinstance(times, list):
            return None
        if not isinstance(winds, list):
            return None
        if not isinstance(rains, list):
            return None
        if not isinstance(precip, list):
            return None
        if not isinstance(snows, list):
            return None

        length = min(
            len(times),
            len(winds),
            len(rains),
            len(precip),
            len(snows),
        )
        if length == 0:
            return None
        hourly_rows = []
        for index in range(length):
            try:
                when = datetime.fromisoformat(str(times[index]).replace("Z", "+00:00"))
                if when.tzinfo is None:
                    when = when.replace(tzinfo=UTC)
                wind = float(winds[index])
                # Open-Meteo rain/precipitation are mm/hour; convert to inches/hour.
                rain_mm = float(rains[index] if rains[index] is not None else precip[index])
                snow_cm = float(snows[index])
                values = (wind, rain_mm, snow_cm)
                if not all(isfinite(value) and value >= 0 for value in values):
                    continue
                hourly_rows.append(
                    {
                        "time": when.astimezone(UTC).isoformat(),
                        "wind_mph": wind,
                        "rain_in_hr": rain_mm / 25.4,
                        "snow_in_hr": snow_cm / 2.54,
                    }
                )
            except (TypeError, ValueError, OverflowError):
                continue
        if not hourly_rows:
            return None
        return {"hourly": hourly_rows}

    @staticmethod
    def at_time(forecast: dict[str, Any], eta: datetime) -> dict[str, Any]:
        """Pick the nearest forecast hour; clamp beyond horizon and flag extrapolation."""
        rows = forecast.get("hourly", [])
        if not rows:
            raise WeatherProviderError("No hourly forecast data available")
        target = eta.astimezone(UTC)
        parsed = [(datetime.fromisoformat(row["time"]), row) for row in rows]
        first_time, last_time = parsed[0][0], parsed[-1][0]
        extrapolated = target < first_time or target > last_time
        if target <= first_time:
            selected = parsed[0][1]
        elif target >= last_time:
            selected = parsed[-1][1]
        else:
            selected = min(parsed, key=lambda item: abs((item[0] - target).total_seconds()))[1]
        return {
            "wind_mph": selected["wind_mph"],
            "rain_in_hr": selected["rain_in_hr"],
            "snow_in_hr": selected["snow_in_hr"],
            "forecast_time": selected["time"],
            "extrapolated": extrapolated,
        }
