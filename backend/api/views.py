"""HTTP endpoints with explicit validation and provider error handling."""

from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from api.analysis import analyze_routes as run_analysis
from api.errors import GeocodingError, RoutingError
from api.providers.geocoding import NominatimGeocodingProvider
from api.serializers import AnalyzeRequestSerializer


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
