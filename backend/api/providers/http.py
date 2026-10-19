"""Shared HTTP helpers with explicit timeouts and cache-friendly keys."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import httpx
from django.conf import settings


def cache_key(namespace: str, value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    return f"spotter:{namespace}:{digest}"


def get_json(
    url: str,
    *,
    params: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    try:
        response = httpx.get(
            url,
            params=params,
            headers=headers,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            follow_redirects=True,
        )
        response.raise_for_status()
        return response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise RuntimeError(f"HTTP provider request failed: {exc}") from exc
