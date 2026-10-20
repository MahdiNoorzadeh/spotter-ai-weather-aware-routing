"""Nominatim geocoding adapter. Cache results and identify this application."""

from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import cache

from api.errors import GeocodingError
from api.providers.base import GeocodeSuggestion, GeoPoint
from api.providers.http import cache_key, get_json


class NominatimGeocodingProvider:
    base_url = "https://nominatim.openstreetmap.org/search"

    def search(self, query: str, limit: int = 5) -> list[GeocodeSuggestion]:
        normalized = " ".join(query.split())
        if len(normalized) < 2:
            return []
        if "configure-contact" in settings.NOMINATIM_USER_AGENT.lower():
            raise GeocodingError(
                "Set NOMINATIM_USER_AGENT to identify your app and include a contact "
                "before sending requests to the public Nominatim service."
            )
        limit = min(max(int(limit), 1), 8)
        key = cache_key("geocode", {"q": normalized.casefold(), "limit": limit})
        cached = cache.get(key)
        if cached is not None:
            return [
                GeocodeSuggestion(
                    point=GeoPoint(float(item["lat"]), float(item["lon"]), item["name"]),
                    place_name=item["name"],
                    provider_id=item.get("id"),
                )
                for item in cached
            ]
        # Nominatim's public endpoint has a strict usage policy. Serialize uncached
        # requests to approximately one request per second per cache backend.
        throttle_key = "spotter:nominatim:request-slot"
        while not cache.add(throttle_key, True, timeout=1):
            time.sleep(1.05)
        try:
            payload = get_json(
                self.base_url,
                params={"q": normalized, "format": "jsonv2", "limit": limit, "addressdetails": 1},
                headers={"User-Agent": settings.NOMINATIM_USER_AGENT},
            )
            if not isinstance(payload, list):
                raise GeocodingError("Geocoding provider returned an unexpected response")
            items = []
            for row in payload:
                try:
                    name = str(row["display_name"])
                    lat, lon = float(row["lat"]), float(row["lon"])
                except (KeyError, TypeError, ValueError):
                    continue
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                items.append(
                    {
                        "lat": lat,
                        "lon": lon,
                        "name": name,
                        "id": str(row.get("place_id", "")),
                    }
                )
            cache.set(key, items, settings.GEOCODE_CACHE_SECONDS)
            return [
                GeocodeSuggestion(
                    point=GeoPoint(item["lat"], item["lon"], item["name"]),
                    place_name=item["name"],
                    provider_id=item["id"] or None,
                )
                for item in items
            ]
        except GeocodingError:
            raise
        except (RuntimeError, TypeError, ValueError) as exc:
            raise GeocodingError("Geocoding service is temporarily unavailable") from exc
