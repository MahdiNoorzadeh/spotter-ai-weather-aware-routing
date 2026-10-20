import { useMemo, useState } from 'react'
import Map, { Layer, NavigationControl, Popup, Source, type LayerProps, type MapLayerMouseEvent } from 'react-map-gl/maplibre'
import { Crosshair, Layers3, MapPinned } from 'lucide-react'
import type { Checkpoint, RouteResult } from '../lib/types'

const routeColors = ['#22c99a', '#e8a34b', '#8d82f6']
const riskColors: Record<string, string> = {
  LOW: '#22c99a', MODERATE: '#e8c34b', HIGH: '#f49a4a', SEVERE: '#f06464', NO_TRAVEL: '#b92e47', UNKNOWN: '#8c9699',
}

function asFeature(geometry: RouteResult['geometry']) {
  if (geometry.type === 'Feature') return geometry
  return { type: 'Feature' as const, properties: {}, geometry }
}

function checkpointFeatureCollection(checkpoints: Checkpoint[]) {
  return {
    type: 'FeatureCollection' as const,
    features: checkpoints.map((point, index) => ({
      type: 'Feature' as const,
      properties: { index, mile_marker: point.mile_marker, risk: point.final_level },
      geometry: { type: 'Point' as const, coordinates: [point.lon, point.lat] },
    })),
  }
}

interface Props { routes: RouteResult[]; selectedRouteId: string | null }
export default function RouteMap({ routes, selectedRouteId }: Props) {
  const [popup, setPopup] = useState<Checkpoint | null>(null)
  const selectedRoute = routes.find((route) => route.id === selectedRouteId) ?? routes[0]
  const [showCheckpoints, setShowCheckpoints] = useState(true)
  const initialView = useMemo(() => {
    const coords = selectedRoute ? asFeature(selectedRoute.geometry).geometry.coordinates : []
    if (!coords.length) return { longitude: -98.5, latitude: 39.5, zoom: 3.2 }
    const middle = coords[Math.floor(coords.length / 2)]
    return { longitude: middle[0], latitude: middle[1], zoom: 4.3 }
  }, [selectedRoute?.id])

  const lineLayer = (id: string, color: string, width: number, opacity: number): LayerProps => ({
    id, type: 'line', layout: { 'line-join': 'round', 'line-cap': 'round' },
    paint: { 'line-color': color, 'line-width': width, 'line-opacity': opacity },
  })
  const pointLayer: LayerProps = {
    id: 'checkpoint-points', type: 'circle',
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 2, 3, 8, 6],
      'circle-color': ['match', ['get', 'risk'], 'LOW', riskColors.LOW, 'MODERATE', riskColors.MODERATE, 'HIGH', riskColors.HIGH, 'SEVERE', riskColors.SEVERE, 'NO_TRAVEL', riskColors.NO_TRAVEL, riskColors.UNKNOWN],
      'circle-stroke-color': '#10201f', 'circle-stroke-width': 1.5,
    },
  }

  return (
    <div className="map-shell">
      <div className="map-topbar"><div className="map-title"><MapPinned size={16} /><span>Route intelligence map</span><span className="live-map-dot" /></div><div className="map-actions"><button type="button" onClick={() => setShowCheckpoints((value) => !value)} className={showCheckpoints ? 'map-action active' : 'map-action'}><Layers3 size={14} /> Checkpoints</button></div></div>
      <Map key={selectedRouteId ?? 'empty'} initialViewState={initialView} interactiveLayerIds={showCheckpoints && selectedRoute ? ['checkpoint-points'] : []} onClick={(event: MapLayerMouseEvent) => { const feature = event.features?.[0]; const index = Number(feature?.properties?.index); if (selectedRoute && Number.isInteger(index) && selectedRoute.checkpoints[index]) setPopup(selectedRoute.checkpoints[index]) }} mapStyle="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json" style={{ width: '100%', height: '100%' }} attributionControl>
        <NavigationControl position="bottom-right" showCompass={false} />
        {routes.map((route, index) => {
          const selected = route.id === selectedRouteId
          return <Source key={route.id} id={`source-${route.id}`} type="geojson" data={asFeature(route.geometry) as never}>
            <Layer {...lineLayer(`line-shadow-${route.id}`, '#142221', selected ? 9 : 5, selected ? 0.9 : 0.35)} />
            <Layer {...lineLayer(`line-${route.id}`, route.id === selectedRouteId ? routeColors[0] : routeColors[(index % routeColors.length)], selected ? 5 : 2.5, selected ? 1 : 0.55)} />
          </Source>
        })}
        {selectedRoute && showCheckpoints && <Source id="checkpoint-source" type="geojson" data={checkpointFeatureCollection(selectedRoute.checkpoints) as never}>
          <Layer {...pointLayer} />
        </Source>}
        {popup && <Popup longitude={popup.lon} latitude={popup.lat} closeButton onClose={() => setPopup(null)} anchor="bottom" offset={10}>
          <div className="checkpoint-popup"><strong>Mile {popup.mile_marker.toFixed(1)}</strong><span className={`risk-text risk-text-${popup.final_level.toLowerCase().replace('_', '-')}`}>{popup.final_level.replace('_', ' ')}</span><p>{new Date(popup.eta).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })}</p>{popup.weather && <p>Wind {popup.weather.wind_mph.toFixed(0)} mph · Rain {popup.weather.rain_in_hr.toFixed(2)} in/hr · Snow {popup.weather.snow_in_hr.toFixed(2)} in/hr</p>}<ul>{popup.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>
        </Popup>}
      </Map>
      {selectedRoute && <div className="map-overlay-legend"><div className="legend-heading">WEATHER RISK</div><div><i style={{ background: riskColors.LOW }} />Low</div><div><i style={{ background: riskColors.MODERATE }} />Moderate</div><div><i style={{ background: riskColors.HIGH }} />High</div><div><i style={{ background: riskColors.SEVERE }} />Severe</div><div><i style={{ background: riskColors.NO_TRAVEL }} />No Travel</div><div><i style={{ background: riskColors.UNKNOWN }} />Unknown</div></div>}
      {!routes.length && <div className="map-empty"><div className="map-empty-icon"><Crosshair size={26} /></div><strong>Your route map starts here</strong><p>Enter an origin and destination to compare route options and weather risk.</p></div>}
    </div>
  )
}
