"""Input validation for the public API."""

from __future__ import annotations

from rest_framework import serializers


class LocationInputSerializer(serializers.Serializer):
    lat = serializers.FloatField(min_value=-90, max_value=90)
    lon = serializers.FloatField(min_value=-180, max_value=180)
    label = serializers.CharField(required=False, allow_blank=True, max_length=250)


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(required=False, allow_blank=False, max_length=250)
    destination = serializers.CharField(required=False, allow_blank=False, max_length=250)
    origin_point = LocationInputSerializer(required=False)
    destination_point = LocationInputSerializer(required=False)
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.FloatField(min_value=0, max_value=200000)
    interval_miles = serializers.ChoiceField(choices=(10, 25, 50), required=False)

    def validate(self, attrs: dict) -> dict:
        for name in ("origin", "destination"):
            point_name = f"{name}_point"
            if not attrs.get(name) and not attrs.get(point_name):
                raise serializers.ValidationError(
                    {name: "Provide a place name or a {lat, lon} point."}
                )
        raw_departure = str(self.initial_data.get("departure_time", ""))
        # Require an explicit Z or numeric UTC offset in the submitted ISO-8601 value.
        has_timezone = (
            raw_departure.endswith(("Z", "z"))
            or "+" in raw_departure[10:]
            or "-" in raw_departure[10:]
        )
        if not has_timezone:
            raise serializers.ValidationError(
                {"departure_time": "Must be an ISO-8601 datetime with timezone."}
            )
        departure = attrs["departure_time"]
        if departure.tzinfo is None or departure.utcoffset() is None:
            raise serializers.ValidationError(
                {"departure_time": "Must be an ISO-8601 datetime with timezone."}
            )
        return attrs


class HeatmapRequestSerializer(serializers.Serializer):
    """Query-string validation for the preloaded weather corridor heatmap."""

    origin = serializers.CharField(required=False, allow_blank=False, max_length=250)
    destination = serializers.CharField(required=False, allow_blank=False, max_length=250)
    origin_lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    origin_lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    destination_lat = serializers.FloatField(required=False, min_value=-90, max_value=90)
    destination_lon = serializers.FloatField(required=False, min_value=-180, max_value=180)
    departure_time = serializers.DateTimeField()
    load_weight_lb = serializers.FloatField(min_value=0, max_value=200000)
    sample_interval_miles = serializers.ChoiceField(
        choices=(10, 20, 25, 50), required=False, default=20
    )

    def validate(self, attrs: dict) -> dict:
        for name in ("origin", "destination"):
            lat_name, lon_name = f"{name}_lat", f"{name}_lon"
            has_lat, has_lon = lat_name in attrs, lon_name in attrs
            if has_lat != has_lon:
                raise serializers.ValidationError(
                    {name: f"Provide both {lat_name} and {lon_name}."}
                )
            if not attrs.get(name) and not (has_lat and has_lon):
                raise serializers.ValidationError(
                    {name: "Provide a place name or its latitude/longitude coordinates."}
                )
        raw_departure = str(self.initial_data.get("departure_time", ""))
        has_timezone = (
            raw_departure.endswith(("Z", "z"))
            or "+" in raw_departure[10:]
            or "-" in raw_departure[10:]
        )
        departure = attrs["departure_time"]
        if not has_timezone or departure.tzinfo is None or departure.utcoffset() is None:
            raise serializers.ValidationError(
                {"departure_time": "Must be an ISO-8601 datetime with timezone."}
            )
        return attrs
