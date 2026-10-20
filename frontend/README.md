# Spotter — Weather-aware truck routing frontend

React 18 + TypeScript + Vite frontend for the Phase 2 Django REST API.

## Requirements

- Node.js 20+ (tested project target: Node 24)
- npm
- Django backend running on `http://127.0.0.1:8000`

## Install and run

From this directory:

```powershell
npm install
npm run dev
```

Open `http://localhost:5173`.

The Vite dev server proxies `/api` requests to `http://127.0.0.1:8000`. Start Django in another terminal from the repository's `backend` directory using your existing virtual environment:

```powershell
python manage.py runserver 127.0.0.1:8000
```

If the backend runs at a different origin, set `VITE_API_BASE_URL` in `.env.local`, for example:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Restart Vite after changing environment variables.

## Commands

```powershell
npm run typecheck
npm run build
npm run preview
```

## Implemented frontend

- Place autocomplete using `GET /api/geocode?q=`.
- Route analysis using `POST /api/routes/analyze`, with timezone-aware departure ISO-8601, load weight, and interval selection.
- Route comparison cards, recommendation and partial-weather/no-safe-route notices.
- MapLibre map with GeoJSON route lines and risk-colored checkpoint circles, plus checkpoint details.
- Checkpoint conditions table, loading/error/empty states, responsive layout, keyboard focus styling, and mobile trip configuration toggle.
- TanStack Query for geocoding requests and Zustand for shared analysis/selection state.

## Backend contract notes

This frontend deliberately matches the API present in the uploaded Phase 2 backend source: `/api/geocode` and `/api/routes/analyze`. The provided backend source does **not** contain `GET /api/heatmap` or a heatmap-frame response contract, so a truthful 0–48 hour forecast heatmap/player cannot yet be wired to the API. That is a Phase 4 backend integration item, not mocked as real forecast data here.

The map uses CARTO's public Positron style and OpenStreetMap-derived map data. It requires network access to the map style/tiles. For production, review the tile provider's usage policy and configure a suitable hosted style.
