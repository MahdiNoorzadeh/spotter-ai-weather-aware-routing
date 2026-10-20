import { create } from 'zustand'
import type { AnalyzeResponse } from './types'

interface RoutingState {
  analysis: AnalyzeResponse | null
  selectedRouteId: string | null
  setAnalysis: (analysis: AnalyzeResponse | null) => void
  selectRoute: (routeId: string | null) => void
}

export const useRoutingStore = create<RoutingState>((set) => ({
  analysis: null,
  selectedRouteId: null,
  setAnalysis: (analysis) => set({ analysis, selectedRouteId: analysis?.recommended_route_id ?? null }),
  selectRoute: (selectedRouteId) => set({ selectedRouteId }),
}))
