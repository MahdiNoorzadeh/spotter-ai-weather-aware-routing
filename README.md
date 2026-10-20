
# Spotter AI — Weather-Aware Truck Routing

Spotter AI is a weather-aware truck route analysis application. It compares available routes using forecast weather conditions, truck load weight, checkpoint-level risk assessments, and estimated arrival times.

The project includes a Django REST API and a React frontend with an interactive map and a 49-frame weather-risk heatmap covering hour offsets 0–48.

## Features

- **Route analysis:** Compare available routes using weather-aware risk summaries and estimated travel times.
- **Weather risk assessment:** Classify wind, rainfall, and snowfall conditions, with additional wind-risk rules based on truck load weight.
- **Route recommendations:** Rank routes using risk severity, affected mileage, and travel time.
- **Checkpoint analysis:** Display weather conditions, estimated arrival times, risk levels, and explanations along each route.
- **Weather-risk heatmap:** Inspect forecast risk across 49 hourly frames, with interactive playback and time selection.
- **Geocoding:** Resolve place names into geographic coordinates.
- **Caching:** Cache geocoding, routing, and weather responses using Django's cache framework, with optional Redis support.
- **Provider fallback:** Prefer Mapbox Directions when configured; otherwise, use the public OSRM demo service.

## Technology stack

### Backend

- Python 3.14
- Django 5.2
- Django REST Framework
- HTTPX
- Open-Meteo weather data
- Nominatim geocoding
- Mapbox Directions / OSRM routing
- Pytest, pytest-django, Ruff, and Black

### Frontend

- React 18
- TypeScript
- Vite
- Tailwind CSS
- MapLibre GL
- TanStack Query
- Zustand

## Requirements

- Python 3.14
- Node.js 20 or later and npm
- Internet access for external routing, geocoding, weather, and map resources
- A Mapbox access token is optional; OSRM is used when one is not configured
- Redis is optional; Django's local-memory cache is used by default

The commands below use Windows PowerShell.

## Backend setup

From the repository root:

```powershell
Set-Location D:\spotter-phase1\backend

py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

Copy-Item .env.example .env
```

Open `backend\.env` and review its settings before running the server. In particular:

- Set a strong, unique `DJANGO_SECRET_KEY`.
- Configure `DJANGO_ALLOWED_HOSTS` for the hosts you intend to use.
- Configure `NOMINATIM_USER_AGENT` with an application identifier and a valid contact address.
- Set `MAPBOX_ACCESS_TOKEN` if you want to use Mapbox Directions.
- Set `REDIS_URL` only if Redis is available and you want to use it.

The Django settings load the backend `.env` file. Do not commit `.env` or any other file containing credentials.

Run the configuration check and tests:

```powershell
python manage.py check
python -m pytest
```

Start the API:

```powershell
python manage.py runserver 127.0.0.1:8000
```

Keep this terminal open while using the frontend.

## Frontend setup

Open a second PowerShell terminal:

```powershell
Set-Location D:\spotter-phase1\frontend

npm install
npm run dev
```

Open the local address printed by Vite, normally:

`http://127.0.0.1:5173`

The Vite development server proxies `/api` requests to the Django backend at `http://127.0.0.1:8000`.

If the backend uses a different address, configure `VITE_API_BASE_URL` in `frontend\.env.local` and restart Vite.

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/geocode?q=Berlin` | Find geographic locations by name |
| POST | `/api/routes/analyze` | Analyze and compare routes |
| GET | `/api/heatmap` | Retrieve forecast heatmap frames |

See [README-PHASE2.md](README-PHASE2.md) for the routing and weather API contract, and [README-PHASE4.md](README-PHASE4.md) for the heatmap request and response format.

## Development checks

Run backend checks from `backend\` with the virtual environment activated:

```powershell
python manage.py check
python -m pytest
ruff check routing api config
black --check routing api config
```

Run frontend checks from `frontend\`:

```powershell
npm run typecheck
npm run build
```

`npm run build` performs TypeScript project checks before creating the production frontend bundle.

## Configuration and external services

- **Open-Meteo:** Supplies forecast weather data.
- **Nominatim:** Provides geocoding. Respect its public-service usage policy and configure an identifying User-Agent.
- **Mapbox Directions:** Optional routing provider when a valid access token is configured.
- **OSRM:** Public fallback routing service; its demo endpoint has no production SLA.
- **CARTO / OpenStreetMap-derived map resources:** The frontend requires network access to load its map style and map tiles.
- **Redis:** Optional shared cache backend. Without `REDIS_URL`, the application uses Django's local-memory cache.

External providers can impose usage limits, return incomplete data, or be unavailable. Missing weather data is represented as unknown rather than being treated as safe.

## Deployment

The repository's local development configuration is not, by itself, a production deployment configuration. Before deploying, configure production secrets, allowed hosts, CORS origins, HTTPS and secure cookies, cache infrastructure, provider usage, and the frontend's production API URL. Run Django's deployment checks against the actual production settings.

Do not expose secret keys, API tokens, or environment files in source control.
