import pytest

from routing.risk import (
    RiskLevel,
    apply_load_rules,
    assess_weather,
    classify_rain,
    classify_snow,
    classify_wind,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, RiskLevel.LOW),
        (24.999, RiskLevel.LOW),
        (25, RiskLevel.MODERATE),
        (34.999, RiskLevel.MODERATE),
        (35, RiskLevel.HIGH),
        (44.999, RiskLevel.HIGH),
        (45, RiskLevel.SEVERE),
        (54.999, RiskLevel.SEVERE),
        (55, RiskLevel.NO_TRAVEL),
        (100, RiskLevel.NO_TRAVEL),
    ],
)
def test_wind_boundaries(value, expected):
    assert classify_wind(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, RiskLevel.LOW),
        (0.09999, RiskLevel.LOW),
        (0.10, RiskLevel.MODERATE),
        (0.24999, RiskLevel.MODERATE),
        (0.25, RiskLevel.HIGH),
        (0.49999, RiskLevel.HIGH),
        (0.50, RiskLevel.SEVERE),
        (1.00, RiskLevel.SEVERE),
        (1.00001, RiskLevel.NO_TRAVEL),
    ],
)
def test_rain_boundaries(value, expected):
    assert classify_rain(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, RiskLevel.LOW),
        (0.49999, RiskLevel.LOW),
        (0.5, RiskLevel.MODERATE),
        (0.99999, RiskLevel.MODERATE),
        (1.0, RiskLevel.HIGH),
        (1.99999, RiskLevel.HIGH),
        (2.0, RiskLevel.SEVERE),
        (3.0, RiskLevel.SEVERE),
        (3.00001, RiskLevel.NO_TRAVEL),
    ],
)
def test_snow_boundaries(value, expected):
    assert classify_snow(value) == expected


@pytest.mark.parametrize("bad", [-1, float("nan"), float("inf"), "invalid", None])
def test_wind_rejects_invalid_measurements(bad):
    with pytest.raises(ValueError):
        classify_wind(bad)


def test_load_rule_wind_50_and_35000_is_no_travel():
    level, reasons = apply_load_rules(RiskLevel.SEVERE, 50, 35_000)
    assert level == RiskLevel.NO_TRAVEL
    assert reasons


def test_load_rule_wind_40_and_45000_is_at_least_severe():
    level, _ = apply_load_rules(RiskLevel.HIGH, 40, 45_000)
    assert level == RiskLevel.SEVERE


def test_load_rule_wind_40_and_35000_remains_high():
    level, reasons = apply_load_rules(RiskLevel.HIGH, 40, 35_000)
    assert level == RiskLevel.HIGH
    assert reasons == ()


def test_load_rule_wind_45_and_exactly_30000_does_not_override():
    level, reasons = apply_load_rules(RiskLevel.SEVERE, 45, 30_000)
    assert level == RiskLevel.SEVERE
    assert reasons == ()


def test_load_rule_wind_35_and_exactly_40000_does_not_override():
    level, reasons = apply_load_rules(RiskLevel.HIGH, 35, 40_000)
    assert level == RiskLevel.HIGH
    assert reasons == ()


def test_wind_55_is_no_travel_even_for_zero_load():
    level, _ = apply_load_rules(RiskLevel.LOW, 55, 0)
    assert level == RiskLevel.NO_TRAVEL


def test_assessment_uses_worst_weather_factor_and_preserves_base_level():
    result = assess_weather(20, 0.3, 0.1, 10_000)
    assert result.wind_level == RiskLevel.LOW
    assert result.rain_level == RiskLevel.HIGH
    assert result.snow_level == RiskLevel.LOW
    assert result.base_level == RiskLevel.HIGH
    assert result.level == RiskLevel.HIGH
