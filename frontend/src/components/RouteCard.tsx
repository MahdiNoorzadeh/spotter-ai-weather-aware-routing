import { ArrowUpRight, Clock3, Route as RouteIcon, ShieldAlert, ShieldCheck, Wind } from 'lucide-react'
import type { RouteResult } from '../lib/types'

interface Props {
  route: RouteResult
  recommended: boolean
  selected: boolean
  onSelect: () => void
}

const riskItems = [
  { key: 'no_travel_miles', label: 'No travel', color: 'risk-no-travel' },
  { key: 'severe_miles', label: 'Severe', color: 'risk-severe' },
  { key: 'high_miles', label: 'High', color: 'risk-high' },
  { key: 'moderate_miles', label: 'Moderate', color: 'risk-moderate' },
  { key: 'low_miles', label: 'Low', color: 'risk-low' },
] as const

export default function RouteCard({ route, recommended, selected, onSelect }: Props) {
  const total = Math.max(route.distance_mi, 1)
  const duration = Math.round(route.duration_min)
  return (
    <button type="button" className={`route-card ${selected ? 'selected' : ''}`} onClick={onSelect} aria-pressed={selected}>
      <div className="route-card-top">
        <div className="route-card-title">
          <span className={`route-number ${recommended ? 'route-number-recommended' : ''}`}>{route.id.replace('route-', 'R')}</span>
          <div><div className="route-name">Route {route.id.replace('route-', '')}</div><div className="route-provider">via {route.provider}</div></div>
        </div>
        {recommended ? <span className="recommended-pill"><ShieldCheck size={12} /> Recommended</span> : <ArrowUpRight size={16} className="route-open-icon" />}
      </div>
      <div className="route-stats">
        <div><RouteIcon size={15} /><strong>{Math.round(route.distance_mi).toLocaleString()}</strong><span>mi</span></div>
        <div><Clock3 size={15} /><strong>{Math.floor(duration / 60)}h {duration % 60}m</strong></div>
        <div><Wind size={15} /><strong>{route.summary.unknown_miles > 0 ? 'Partial' : 'Forecast'}</strong></div>
      </div>
      <div className="risk-bar" aria-label="Route risk breakdown">
        {riskItems.map((item) => {
          const miles = route.summary[item.key]
          return miles > 0 ? <span key={item.key} className={`risk-segment ${item.color}`} style={{ width: `${Math.max((miles / total) * 100, 1.5)}%` }} title={`${item.label}: ${miles.toFixed(1)} mi`} /> : null
        })}
      </div>
      <div className="risk-legend">
        {riskItems.filter((item) => route.summary[item.key] > 0).slice(0, 3).map((item) => <span key={item.key}><i className={`legend-dot ${item.color}`} />{route.summary[item.key].toFixed(0)} mi {item.label.toLowerCase()}</span>)}
        {route.summary.unknown_miles > 0 && <span><i className="legend-dot risk-unknown" />{route.summary.unknown_miles.toFixed(0)} mi unknown</span>}
      </div>
      <div className="route-card-bottom">
        <span>{route.checkpoints.length} weather checkpoints</span>
        <span className="inspect-route">{selected ? 'Viewing on map' : 'Inspect route'} <ArrowUpRight size={13} /></span>
      </div>
      {route.summary.no_travel_miles > 0 && <div className="route-warning"><ShieldAlert size={14} /> {route.summary.no_travel_miles.toFixed(1)} miles marked No Travel</div>}
    </button>
  )
}
