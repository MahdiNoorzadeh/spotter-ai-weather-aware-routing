# Spotter AI — Phase 4: Weather-risk heatmap

## What changed

- Adds `GET /api/heatmap`, returning 49 frames (`hour_offset` 0–48) in one response.
- Samples each available route at 20-mile intervals and adds two corridor points approximately 3 miles either side of the centerline.
- Reuses the existing Open-Meteo provider, its coordinate cache/batching, and `routing.risk.assess_weather` so heatmap risk and checkpoint risk share the same classification and load overrides.
- Unknown weather is explicitly marked `risk_level: "UNKNOWN"`, with intensity 3 so unavailable data is not rendered as safe.
- Connects the frontend slider and play/pause controls to the preloaded frames. Slider scrubbing only swaps the GeoJSON data already in memory; it does not issue additional requests.
- Keeps route analysis usable if the heatmap request fails.

## API

Example (coordinate-based request):

```http
GET /api/heatmap?origin_lat=53.5511&origin_lon=9.9937&destination_lat=52.52&destination_lon=13.405&departure_time=2026-10-21T09%3A00%3A00%2B02%3A00&load_weight_lb=40000&sample_interval_miles=20
```

Use either `origin` and `destination` place names, or coordinate pairs `origin_lat` + `origin_lon` and `destination_lat` + `destination_lon`. `departure_time` must be ISO-8601 with an explicit timezone. `load_weight_lb` must be between 0 and 200,000. `sample_interval_miles` is optional and accepts 10, 20, 25, or 50; the frontend currently requests 20.

Response shape:

```json
{
  "departure_time": "2026-10-21T09:00:00+02:00",
  "frame_count": 49,
  "sample_count": 80,
  "route_count": 3,
  "weather_partial_failure": false,
  "frames": [
    {
      "hour_offset": 0,
      "timestamp": "2026-10-21T09:00:00+02:00",
      "geojson": {
        "type": "FeatureCollection",
        "features": [
          {
            "type": "Feature",
            "properties": {
              "hour_offset": 0,
              "intensity": 0,
              "risk_level": "LOW",
              "wind_mph": 10.0,
              "rain_in_hr": 0.0,
              "snow_in_hr": 0.0,
              "weather_status": "ok",
              "extrapolated": false
            },
            "geometry": { "type": "Point", "coordinates": [9.9937, 53.5511] }
          }
        ]
      }
    }
  ]
}
```

The response example is abbreviated: the real response contains all 49 frames and all corridor points. Intensity values follow the shared risk enum: Low 0, Moderate 1, High 2, Severe 3, No Travel 4. Unavailable data is labeled `UNKNOWN` and assigned intensity 3 conservatively.

## Verify on Windows PowerShell

1. Extract the Phase 4 patch ZIP into `D:\spotter-phase1`, allowing files to overwrite.
2. Keep the existing ignored `backend\.env` file. Do not replace it with any file from the patch.
3. In one PowerShell terminal:

   ```powershell
   cd D:\spotter-phase1\backend
   .\.venv\Scripts\Activate.ps1
   python -m pytest
   ruff check routing api config
   black --check routing api config
   ```

4. Restart Django if it was already running:

   ```powershell
   python manage.py runserver
   ```

5. In another terminal, from `D:\spotter-phase1\frontend`, run:

   ```powershell
   npm run typecheck
   npm run build
   npm run dev
   ```

6. In the UI, analyze a route. The heatmap should load after route analysis, display its loaded-frame status, enable the slider and Play/Pause control, and render colored risk intensity on the map. Move the slider from 0 to 48 and confirm the displayed local timestamp changes. Toggling `HEATMAP ON/OFF` should hide/show the heat layer without removing route lines or checkpoint markers.

## Limitations

- The heatmap makes a separate route-provider request (normally served from the existing route cache) because route candidates are not persisted server-side between HTTP requests.
- Corridor width is approximated with centerline points and two lateral samples; it is not a meteorological grid or road-weather model.
- Open-Meteo forecasts are hourly and finite-horizon. The existing provider flags forecast values clamped outside the available forecast range as extrapolated.
- Snowfall is interpreted as snow depth per hour, matching the existing provider and risk module.
