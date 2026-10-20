"""HTTP endpoints with explicit validation and provider error handling."""

from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.analysis import analyze_routes as run_analysis
from api.errors import GeocodingError, RoutingError
from api.heatmap import build_heatmap
from api.providers.geocoding import NominatimGeocodingProvider
from api.serializers import AnalyzeRequestSerializer, HeatmapRequestSerializer


@api_view(["GET"])
def geocode(request):
    query = request.query_params.get("q", "").strip()
    if len(query) < 2:
        return Response(
            {
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "q must contain at least 2 characters.",
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        suggestions = NominatimGeocodingProvider().search(query, limit=5)
    except GeocodingError as exc:
        return Response(
            {"error": {"code": "GEOCODING_UNAVAILABLE", "message": str(exc)}},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    return Response(
        {
            "suggestions": [
                {
                    "label": item.place_name,
                    "lat": item.point.lat,
                    "lon": item.point.lon,
                    "provider_id": item.provider_id,
                }
                for item in suggestions
            ]
        }
    )


@api_view(["POST"])
def analyze_routes_view(request):
    serializer = AnalyzeRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        return Response(run_analysis(serializer.validated_data))
    except GeocodingError as exc:
        return Response(
            {"error": {"code": "GEOCODING_ERROR", "message": str(exc)}},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except RoutingError as exc:
        return Response(
            {"error": {"code": "ROUTING_UNAVAILABLE", "message": str(exc)}},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception:
        # Do not leak third-party response bodies, tokens, or stack traces to clients.
        return Response(
            {
                "error": {
                    "code": "ANALYSIS_FAILED",
                    "message": "Route analysis failed unexpectedly. Please retry.",
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# URL configuration imports this public name.
analyze_routes = analyze_routes_view


@api_view(["GET"])
def heatmap_view(request):
    """Return all 49 hourly risk frames so slider scrubbing stays client-side."""
    serializer = HeatmapRequestSerializer(data=request.query_params)
    if not serializer.is_valid():
        return Response(
            {"error": {"code": "VALIDATION_ERROR", "details": serializer.errors}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        values = serializer.validated_data
        return Response(
            build_heatmap(
                origin=values.get("origin"),
                destination=values.get("destination"),
                origin_lat=values.get("origin_lat"),
                origin_lon=values.get("origin_lon"),
                destination_lat=values.get("destination_lat"),
                destination_lon=values.get("destination_lon"),
                departure_time=values["departure_time"],
                load_weight_lb=values["load_weight_lb"],
                sample_interval_miles=values.get("sample_interval_miles", 20),
            )
        )
    except GeocodingError as exc:
        return Response(
            {"error": {"code": "GEOCODING_ERROR", "message": str(exc)}},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
    except RoutingError as exc:
        return Response(
            {"error": {"code": "ROUTING_UNAVAILABLE", "message": str(exc)}},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception:
        # Do not expose third-party payloads, credentials, or stack traces.
        return Response(
            {
                "error": {
                    "code": "HEATMAP_FAILED",
                    "message": "Heatmap generation failed unexpectedly. Please retry.",
                }
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
