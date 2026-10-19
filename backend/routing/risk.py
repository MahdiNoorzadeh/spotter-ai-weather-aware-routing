"""Pure weather-risk classification and truck-load overrides.

No Django or network dependencies. Risk levels are ordered from safest to worst.
Thresholds use lower-inclusive, upper-exclusive intervals.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from math import isfinite


class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    wind_level: RiskLevel
    rain_level: RiskLevel
    snow_level: RiskLevel
    reasons: tuple[str, ...]
    base_level: RiskLevel


def _validate_measurement(value: float, name: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not isfinite(numeric) or numeric < 0:
        raise ValueError(f"{name} must be a finite, non-negative number")
    return numeric


def classify_wind(wind_mph: float) -> RiskLevel:
    """Classify sustained wind speed in mph."""
    value = _validate_measurement(wind_mph, "wind_mph")
    if value < 25:
        return RiskLevel.LOW
    if value < 35:
        return RiskLevel.MODERATE
    if value < 45:
        return RiskLevel.HIGH
    if value < 55:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_rain(rain_in_hr: float) -> RiskLevel:
    """Classify precipitation rate in inches per hour."""
    value = _validate_measurement(rain_in_hr, "rain_in_hr")
    if value < 0.10:
        return RiskLevel.LOW
    if value < 0.25:
        return RiskLevel.MODERATE
    if value < 0.50:
        return RiskLevel.HIGH
    if value <= 1.00:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def classify_snow(snow_in_hr: float) -> RiskLevel:
    """Classify snowfall rate in inches per hour (snow depth, not liquid equivalent)."""
    value = _validate_measurement(snow_in_hr, "snow_in_hr")
    if value < 0.5:
        return RiskLevel.LOW
    if value < 1.0:
        return RiskLevel.MODERATE
    if value < 2.0:
        return RiskLevel.HIGH
    if value <= 3.0:
        return RiskLevel.SEVERE
    return RiskLevel.NO_TRAVEL


def apply_load_rules(
    base_level: RiskLevel, wind_mph: float, load_weight_lb: float
) -> tuple[RiskLevel, tuple[str, ...]]:
    """Apply the specified load-dependent wind rules without lowering risk."""
    wind = _validate_measurement(wind_mph, "wind_mph")
    load = _validate_measurement(load_weight_lb, "load_weight_lb")
    reasons: list[str] = []

    if wind >= 55:
        reasons.append("Wind >= 55 mph: No Travel for any load")
        return RiskLevel.NO_TRAVEL, tuple(reasons)

    if 45 <= wind < 55 and load > 30_000:
        reasons.append("Wind 45-54.99 mph with load > 30,000 lb: No Travel")
        return max(base_level, RiskLevel.NO_TRAVEL), tuple(reasons)

    if 35 <= wind < 45 and load > 40_000:
        reasons.append("Wind 35-44.99 mph with load > 40,000 lb: at least Severe")
        return max(base_level, RiskLevel.SEVERE), tuple(reasons)

    return base_level, tuple(reasons)


def assess_weather(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_weight_lb: float,
) -> RiskAssessment:
    """Return independent factor classifications and the final worst-case risk."""
    wind = classify_wind(wind_mph)
    rain = classify_rain(rain_in_hr)
    snow = classify_snow(snow_in_hr)
    base = max(wind, rain, snow)
    final, load_reasons = apply_load_rules(base, wind_mph, load_weight_lb)

    reasons: list[str] = []
    if wind == base:
        reasons.append(f"Wind classified as {wind.name.replace('_', ' ').title()}")
    if rain == base:
        reasons.append(f"Rain classified as {rain.name.replace('_', ' ').title()}")
    if snow == base:
        reasons.append(f"Snow classified as {snow.name.replace('_', ' ').title()}")
    reasons.extend(load_reasons)

    return RiskAssessment(
        level=final,
        wind_level=wind,
        rain_level=rain,
        snow_level=snow,
        reasons=tuple(reasons),
        base_level=base,
    )


def risk_score(level: RiskLevel) -> int:
    """Numeric score used by mileage-weighted route averages."""
    return int(RiskLevel(level))


def classify_weather(
    wind_mph: float,
    rain_in_hr: float,
    snow_in_hr: float,
    load_weight_lb: float,
) -> RiskAssessment:
    """Descriptive alias for callers that prefer the full classification name."""
    return assess_weather(wind_mph, rain_in_hr, snow_in_hr, load_weight_lb)
