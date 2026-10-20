import { useMemo, useState } from 'react'
import { AlertTriangle, ArrowDownUp, ArrowRight, CalendarClock, Check, ChevronDown, CloudSun, Compass, LoaderCircle, Menu, Navigation, Pause, Play, RefreshCw, ShieldCheck, SlidersHorizontal, Truck, X } from 'lucide-react'
import PlaceInput from './components/PlaceInput'
import RouteCard from './components/RouteCard'
import RouteMap from './components/RouteMap'
import { analyzeRoutes, type AnalyzeInput } from './lib/api'
import type { GeocodeSuggestion } from './lib/types'
import { useRoutingStore } from './lib/store'

function localDateTimeValue(date = new Date()) {
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function toIsoWithOffset(localValue: string) {
  const date = new Date(localValue)
  const offset = -date.getTimezoneOffset()
  const sign = offset >= 0 ? '+' : '-'
  const abs = Math.abs(offset)
  return `${localValue}:00${sign}${String(Math.floor(abs / 60)).padStart(2, '0')}:${String(abs % 60).padStart(2, '0')}`
}

export default function App() {
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [originPoint, setOriginPoint] = useState<GeocodeSuggestion | null>(null)
  const [destinationPoint, setDestinationPoint] = useState<GeocodeSuggestion | null>(null)
  const [departureTime, setDepartureTime] = useState(localDateTimeValue())
  const [loadWeight, setLoadWeight] = useState('40000')
  const [interval, setInterval] = useState('25')
  const [advancedOpen, setAdvancedOpen] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [mobileFormOpen, setMobileFormOpen] = useState(false)
  const analysis = useRoutingStore((state) => state.analysis)
  const selectedRouteId = useRoutingStore((state) => state.selectedRouteId)
  const setAnalysis = useRoutingStore((state) => state.setAnalysis)
  const selectRoute = useRoutingStore((state) => state.selectRoute)
  const [loading, setLoading] = useState(false)
  const [heatmapHour, setHeatmapHour] = useState(0)

  const selectedRoute = useMemo(() => analysis?.routes.find((route) => route.id === selectedRouteId) ?? null, [analysis, selectedRouteId])
  const handleAnalyze = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    if (!origin.trim() || !destination.trim()) { setError('Enter both an origin and destination.'); return }
    if (origin.trim().toLowerCase() === destination.trim().toLowerCase()) { setError('Origin and destination must be different.'); return }
    const weight = Number(loadWeight)
    if (!Number.isFinite(weight) || weight < 0 || weight > 200000) { setError('Load weight must be between 0 and 200,000 lb.'); return }
    if (!departureTime || Number.isNaN(new Date(departureTime).getTime())) { setError('Choose a valid departure date and time.'); return }
    const input: AnalyzeInput = {
      origin: origin.trim(), destination: destination.trim(),
      ...(originPoint ? { origin_point: { lat: originPoint.lat, lon: originPoint.lon, label: originPoint.label } } : {}),
      ...(destinationPoint ? { destination_point: { lat: destinationPoint.lat, lon: destinationPoint.lon, label: destinationPoint.label } } : {}),
      departure_time: toIsoWithOffset(departureTime), load_weight_lb: weight, interval_miles: Number(interval),
    }
    setLoading(true)
    try {
      const result = await analyzeRoutes(input)
      if (!result.routes?.length) throw new Error('The API returned no route options. Try another pair of locations.')
      setAnalysis(result)
      setMobileFormOpen(false)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Route analysis failed. Please try again.')
    } finally { setLoading(false) }
  }

  const chooseOrigin = (place: GeocodeSuggestion) => { setOrigin(place.label); setOriginPoint(place) }
  const chooseDestination = (place: GeocodeSuggestion) => { setDestination(place.label); setDestinationPoint(place) }
  const swapPlaces = () => {
    setOrigin(destination); setDestination(origin)
    setOriginPoint(destinationPoint); setDestinationPoint(originPoint)
  }

  return (
    <main className="app-shell">
      <header className="top-header">
        <a href="#top" className="brand" aria-label="Spotter home"><span className="brand-mark"><Navigation size={19} /></span><span>spotter<span className="brand-period">.</span></span><span className="brand-divider" /><span className="brand-product">FLEET INTELLIGENCE</span></a>
        <div className="header-right"><span className="system-status"><i /> SYSTEM OPERATIONAL</span><span className="header-separator" /><span className="header-mode"><CloudSun size={15} /> WEATHER-AWARE ROUTING</span><button type="button" className="mobile-menu" aria-label="Toggle route planner" onClick={() => setMobileFormOpen((value) => !value)}>{mobileFormOpen ? <X size={18} /> : <Menu size={18} />}</button></div>
      </header>
      <section className="page-heading" id="top"><div><div className="eyebrow"><span>ROUTE PLANNING</span><i /> <span>WEATHER RISK ANALYSIS</span></div><h1>Plan smarter. <span>Drive safer.</span></h1><p>Compare drivable routes against forecast conditions before your truck leaves the yard.</p></div><div className="heading-chip"><ShieldCheck size={16} /><span>Risk-aware decisions</span></div></section>

      <div className="workspace">
        <aside className={`planner-panel ${mobileFormOpen ? 'mobile-open' : ''}`}>
          <div className="panel-heading"><div className="panel-icon"><Compass size={17} /></div><div><h2>Trip configuration</h2><p>Set up your next haul</p></div><span className="step-indicator">01 <span>/ 01</span></span></div>
          <form onSubmit={handleAnalyze} className="planner-form">
            <div className="form-section-title"><span>ROUTE DETAILS</span><span className="required-note">* Required</span></div>
            <div className="location-stack">
              <PlaceInput label="Origin" placeholder="City, state or address" value={origin} onChange={(value) => { setOrigin(value); setOriginPoint(null) }} onSelect={chooseOrigin} icon="origin" />
              <button className="swap-places" type="button" aria-label="Swap origin and destination" onClick={swapPlaces}><ArrowDownUp size={15} /></button>
              <PlaceInput label="Destination" placeholder="Where is the load going?" value={destination} onChange={(value) => { setDestination(value); setDestinationPoint(null) }} onSelect={chooseDestination} icon="destination" />
            </div>
            <div className="field-block"><label htmlFor="departure-time" className="field-label">Departure date & time</label><div className="input-with-icon"><CalendarClock size={16} /><input id="departure-time" type="datetime-local" value={departureTime} onChange={(event) => setDepartureTime(event.target.value)} required /></div><span className="field-hint">Uses your device's local timezone; sent with UTC offset.</span></div>
            <div className="section-divider" />
            <button className="accordion-heading" type="button" onClick={() => setAdvancedOpen((value) => !value)} aria-expanded={advancedOpen}><span><SlidersHorizontal size={15} /> LOAD & ANALYSIS</span><ChevronDown size={16} className={advancedOpen ? '' : 'chevron-collapsed'} /></button>
            {advancedOpen && <div className="advanced-fields"><div className="field-block"><label htmlFor="load-weight" className="field-label">Total load weight <span className="unit-label">LB</span></label><div className="input-with-icon"><Truck size={16} /><input id="load-weight" type="number" min="0" max="200000" step="1" value={loadWeight} onChange={(event) => setLoadWeight(event.target.value)} required /><span className="input-suffix">lb</span></div><div className="weight-presets"><button type="button" onClick={() => setLoadWeight('0')}>Empty · 0</button><button type="button" onClick={() => setLoadWeight('20000')}>Light · 20k</button><button type="button" onClick={() => setLoadWeight('40000')}>Standard · 40k</button><button type="button" onClick={() => setLoadWeight('80000')}>Heavy · 80k</button></div></div><div className="field-block"><label htmlFor="checkpoint-interval" className="field-label">Weather checkpoint interval</label><div className="select-wrap"><select id="checkpoint-interval" value={interval} onChange={(event) => setInterval(event.target.value)}><option value="10">Every 10 miles — detailed</option><option value="25">Every 25 miles — balanced</option><option value="50">Every 50 miles — overview</option></select><ChevronDown size={15} /></div><span className="field-hint">Closer intervals provide more granular risk attribution.</span></div></div>}
            {error && <div className="error-banner" role="alert"><AlertTriangle size={16} /><span>{error}</span><button type="button" aria-label="Dismiss error" onClick={() => setError(null)}><X size={14} /></button></div>}
            <button className="analyze-button" type="submit" disabled={loading}>{loading ? <><LoaderCircle className="spin" size={17} /> Analyzing routes…</> : <><span>Analyze route options</span><ArrowRight size={17} /></>}</button>
            <p className="form-footnote"><ShieldCheck size={13} /> Forecast data can change. Always follow posted road restrictions.</p>
          </form>
          <div className="panel-footer"><span>POWERED BY</span><div><b>OpenStreetMap</b><i /> <b>Open-Meteo</b><i /> <b>OSRM</b></div></div>
        </aside>

        <section className="results-area" aria-label="Route analysis results">
          <div className="results-topline"><div><h2>{analysis ? 'Route comparison' : 'Route overview'}</h2><p>{analysis ? `${analysis.route_count} route option${analysis.route_count === 1 ? '' : 's'} analyzed for your trip` : 'Your route options and weather intelligence will appear here'}</p></div>{analysis && <button type="button" className="reset-button" onClick={() => { setAnalysis(null); setError(null) }}><RefreshCw size={14} /> Clear results</button>}</div>
          {analysis && <div className="recommendation-banner"><div className="recommendation-icon"><ShieldCheck size={20} /></div><div className="recommendation-copy"><span>SPOTTER RECOMMENDS</span><strong>{analysis.recommended_route_id.replace('route-', 'Route ')}</strong><p>{analysis.recommendation_reason}</p></div><div className="recommendation-badge"><Check size={14} /> BEST AVAILABLE</div></div>}
          {analysis?.no_safe_route && <div className="no-safe-banner"><AlertTriangle size={17} /><div><strong>No route is currently classified as safe.</strong><span>All available options contain No Travel miles. Review the route details and consider delaying departure.</span></div></div>}
          {analysis?.weather_partial_failure && <div className="partial-banner"><AlertTriangle size={15} /><span>Some checkpoint forecasts are unavailable. Unknown segments are treated conservatively in route ranking.</span></div>}
          {analysis?.routes_notice && <div className="partial-banner"><AlertTriangle size={15} /><span>{analysis.routes_notice}</span></div>}

          <div className="map-section"><RouteMap routes={analysis?.routes ?? []} selectedRouteId={selectedRouteId} /></div>
          <section className="heatmap-panel" aria-label="Weather heatmap timeline">
            <div className="heatmap-head"><div className="heatmap-icon"><CloudSun size={17} /></div><div><h3>Forecast heatmap</h3><p>Explore weather-risk conditions over the next 48 hours</p></div><span className="heatmap-unavailable">API NOT CONNECTED</span></div>
            <div className="heatmap-controls"><button type="button" className="heatmap-play" disabled aria-label="Play forecast timeline"><Play size={13} /></button><div className="heatmap-slider-wrap"><div className="heatmap-time-labels"><span>NOW</span><strong>+{heatmapHour} HOURS</strong><span>+48H</span></div><input aria-label="Forecast time offset in hours" type="range" min="0" max="48" value={heatmapHour} onChange={(event) => setHeatmapHour(Number(event.target.value))} disabled /><div className="heatmap-ticks"><span>0h</span><span>12h</span><span>24h</span><span>36h</span><span>48h</span></div></div><button type="button" className="heatmap-play" disabled aria-label="Pause forecast timeline"><Pause size={13} /></button></div>
            <div className="heatmap-notice"><AlertTriangle size={13} /><span>The Phase 2 backend currently exposes route analysis and geocoding only. The 49-frame <code>/api/heatmap</code> endpoint is required to activate this timeline.</span></div>
          </section>

          {analysis ? <>
            <div className="route-list-heading"><div><h3>Available routes <span>{analysis.routes.length.toString().padStart(2, '0')}</span></h3><p>Select a route to inspect its checkpoints on the map.</p></div><div className="sort-label"><span>RANKED BY</span><b>Weather risk <ChevronDown size={13} /></b></div></div>
            <div className="route-cards">{analysis.routes.map((route) => <RouteCard key={route.id} route={route} recommended={route.id === analysis.recommended_route_id} selected={route.id === selectedRouteId} onSelect={() => selectRoute(route.id)} />)}</div>
            {selectedRoute && <section className="checkpoint-section"><div className="checkpoint-heading"><div><h3>Checkpoint conditions</h3><p>{selectedRoute.id.replace('route-', 'Route ')} · {selectedRoute.checkpoints.length} forecast points along the route</p></div><span className="checkpoint-count">{selectedRoute.interval_miles} mi intervals</span></div><div className="checkpoint-table-wrap"><table className="checkpoint-table"><thead><tr><th>Checkpoint</th><th>ETA</th><th>Risk level</th><th>Wind</th><th>Rain / snow</th></tr></thead><tbody>{selectedRoute.checkpoints.map((checkpoint, index) => <tr key={`${checkpoint.mile_marker}-${checkpoint.lat}-${checkpoint.lon}`}><td><span className="mile-marker">{index === 0 ? 'START' : index === selectedRoute.checkpoints.length - 1 ? 'END' : `MI ${checkpoint.mile_marker.toFixed(0)}`}</span></td><td>{new Date(checkpoint.eta).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</td><td><span className={`risk-pill risk-pill-${checkpoint.final_level.toLowerCase().replace('_', '-')}`}><i />{checkpoint.final_level.replace('_', ' ')}</span></td><td>{checkpoint.weather ? `${checkpoint.weather.wind_mph.toFixed(0)} mph` : '—'}</td><td>{checkpoint.weather ? `${checkpoint.weather.rain_in_hr.toFixed(2)} / ${checkpoint.weather.snow_in_hr.toFixed(2)} in/hr` : 'Unavailable'}</td></tr>)}</tbody></table></div></section>}
            <div className="analysis-footnote"><ShieldCheck size={14} /><span>Risk is estimated from forecast wind, rain, snow, and load weight. This is decision support, not a substitute for official road and weather advisories.</span></div>
          </> : <div className="welcome-grid"><div className="welcome-card"><span className="welcome-icon"><CloudSun size={18} /></span><strong>Weather at every mile</strong><p>Forecast conditions are evaluated at estimated arrival time, not just at departure.</p></div><div className="welcome-card"><span className="welcome-icon"><ShieldCheck size={18} /></span><strong>Load-aware risk</strong><p>Risk levels account for wind, rain, snow and the weight you're hauling.</p></div><div className="welcome-card"><span className="welcome-icon"><RouteIconFallback /></span><strong>Compare route options</strong><p>Review alternate routes and see why the safest available option was selected.</p></div></div>}
          <footer className="page-footer"><span>SPOTTER ROUTE INTELLIGENCE <i /> PHASE 3</span><span>Forecasts are indicative and may not reflect live road closures.</span></footer>
        </section>
      </div>
    </main>
  )
}

function RouteIconFallback() { return <Truck size={18} /> }
