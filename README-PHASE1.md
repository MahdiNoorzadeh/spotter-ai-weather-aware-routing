# Spotter AI — Phase 1: Pure Logic

This phase implements and tests the backend's provider-independent business logic. It does not yet create the Django project, external API clients, or frontend.

## Requirements

- Python 3.14
- Windows 10/11 PowerShell

## Setup on Windows

From the repository root:

```powershell
cd backend
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
python -m pytest
```

If PowerShell blocks activation, use this command for the current terminal only:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Expected result: all Phase 1 tests pass. This project targets Python 3.14 and pins Django to 5.2.8 or newer within the Django 5.2 series, because earlier Django 5 releases do not officially support Python 3.14.

## Run checks

```powershell
python -m pytest
ruff check routing
black --check routing
```

To auto-format after reviewing any changes:

```powershell
ruff check --fix routing
black routing
```

## Implemented modules

- `routing/risk.py`: wind/rain/snow classification, load overrides, reasons, and numeric score.
- `routing/recommend.py`: mileage-weighted summaries and deterministic lexicographic ranking.
- `routing/sampling.py`: adaptive checkpoint intervals, endpoint inclusion, midpoint segment mileage attribution, and ETA interpolation.

## Decisions and assumptions

1. Risk levels map to numeric scores: Low=0, Moderate=1, High=2, Severe=3, No Travel=4.
2. All thresholds use lower-inclusive, upper-exclusive boundaries, except the final Severe band includes exactly 1.00 in/hr rain and 3.00 in/hr snow; values above those thresholds are No Travel. Thus rain 0.25 is High and snow 1.0 is High.
3. Load rules are applied after weather classification. Wind >=55 mph is No Travel for any load; wind >=45 and <55 mph with load >30,000 lb is No Travel; wind >=35 and <45 mph with load >40,000 lb is at least Severe. Equality at the load thresholds does not trigger the override.
4. A route with any No Travel miles ranks below every route without No Travel miles. If all candidates have No Travel miles, fewer No Travel miles wins before the remaining criteria.
5. After No Travel handling, routes are compared by Severe miles, High miles, mileage-weighted average risk, and total travel time, in that order.
6. Checkpoint ownership is bounded by the midpoint to each adjacent checkpoint; the first segment starts at mile zero and the last ends at the destination.
7. The adaptive interval is 10 miles for routes <150 miles, 25 miles for routes from 150 through 500 miles inclusive, and 50 miles for routes >500 miles. The caller may explicitly select 10, 25, or 50 miles.
8. ETA uses cumulative route-duration profile points when available, interpolating between them; otherwise it interpolates linearly by distance. Departure datetimes must include a timezone.
9. Snowfall values are expected in inches/hour of snow depth, not liquid-water equivalent. Provider conversion is implemented in Phase 2.

## Known limitations in Phase 1

- The modules assume valid numeric weather values; Phase 2 will define explicit partial-weather failure handling in the API layer.
- Forecast horizon clamping, weather batching/caching, routing providers, geocoding, and heatmap frames are Phase 2/4 work.
- This phase does not create a runnable Django web server yet.
