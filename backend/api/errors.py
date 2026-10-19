"""Typed errors exposed by provider adapters and API views."""


class ProviderError(Exception):
    """A third-party provider failed or returned an invalid response."""


class GeocodingError(ProviderError):
    """A location could not be resolved."""


class RoutingError(ProviderError):
    """A route could not be calculated."""


class WeatherProviderError(ProviderError):
    """A weather request failed."""
