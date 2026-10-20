import type { AnalyzeResponse, GeocodeSuggestion } from './types'

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '')

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.body ? { 'Content-Type': 'application/json' } : {}), ...init?.headers },
    })
  } catch {
    throw new Error('Could not reach the API. Check that the Django backend is running.')
  }
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = payload as { error?: { message?: string; code?: string; details?: unknown } }
    const details = error.error?.details ? ` (${JSON.stringify(error.error.details)})` : ''
    throw new Error(`${error.error?.message ?? error.error?.code ?? `Request failed (${response.status})`}${details}`)
  }
  return payload as T
}

export function searchPlaces(query: string, signal?: AbortSignal) {
  return request<{ suggestions: GeocodeSuggestion[] }>(`/api/geocode?q=${encodeURIComponent(query)}`, { signal })
    .then((result) => result.suggestions)
}

export interface AnalyzeInput {
  origin: string
  destination: string
  origin_point?: { lat: number; lon: number; label: string }
  destination_point?: { lat: number; lon: number; label: string }
  departure_time: string
  load_weight_lb: number
  interval_miles: number
}

export function analyzeRoutes(input: AnalyzeInput) {
  return request<AnalyzeResponse>('/api/routes/analyze', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}
