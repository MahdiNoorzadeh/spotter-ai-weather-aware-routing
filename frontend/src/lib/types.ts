export type RiskLevel = 'NO_TRAVEL' | 'SEVERE' | 'HIGH' | 'MODERATE' | 'LOW' | 'UNKNOWN' | string

export interface GeocodeSuggestion {
  label: string
  lat: number
  lon: number
  provider_id: string | null
}

export interface WeatherAtCheckpoint {
  wind_mph: number
  rain_in_hr: number
  snow_in_hr: number
  forecast_time: string
  extrapolated: boolean
}

export interface Checkpoint {
  lat: number
  lon: number
  mile_marker: number
  eta: string
  weather: WeatherAtCheckpoint | null
  base_level: RiskLevel | null
  final_level: RiskLevel
  reasons: string[]
  weather_status: 'ok' | 'unavailable' | string
}

export interface RouteSummary {
  severe_miles: number
  high_miles: number
  moderate_miles: number
  low_miles: number
  no_travel_miles: number
  unknown_miles: number
  avg_risk: number
  total_time_min: number
  distance_mi: number
}

export interface GeoJsonLine {
  type: 'Feature'
  properties?: Record<string, unknown>
  geometry: {
    type: 'LineString'
    coordinates: [number, number][]
  }
}

export interface RouteResult {
  id: string
  provider: string
  geometry: GeoJsonLine | { type: 'LineString'; coordinates: [number, number][] }
  distance_mi: number
  duration_min: number
  eta_destination: string
  interval_miles: number
  checkpoints: Checkpoint[]
  summary: RouteSummary
}

export interface AnalyzeResponse {
  routes: RouteResult[]
  recommended_route_id: string
  recommendation_reason: string
  no_safe_route: boolean
  route_count: number
  routes_notice: string | null
  weather_partial_failure: boolean
  ranking_order: string[]
}

export interface ApiErrorPayload {
  error?: { code?: string; message?: string; details?: unknown }
}
