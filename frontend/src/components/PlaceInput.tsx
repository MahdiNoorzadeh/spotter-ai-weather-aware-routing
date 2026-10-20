import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapPin, Search, X } from 'lucide-react'
import { searchPlaces } from '../lib/api'
import type { GeocodeSuggestion } from '../lib/types'

interface PlaceInputProps {
  label: string
  placeholder: string
  value: string
  onChange: (value: string) => void
  onSelect: (place: GeocodeSuggestion) => void
  icon: 'origin' | 'destination'
}

export default function PlaceInput({ label, placeholder, value, onChange, onSelect, icon }: PlaceInputProps) {
  const [focused, setFocused] = useState(false)
  const [query, setQuery] = useState(value)
  useEffect(() => setQuery(value), [value])
  const results = useQuery({
    queryKey: ['geocode', query.trim()],
    queryFn: ({ signal }) => searchPlaces(query.trim(), signal),
    enabled: focused && query.trim().length >= 2,
    staleTime: 60_000,
  })
  const showList = focused && query.trim().length >= 2

  return (
    <div className="place-field">
      <label className="field-label" htmlFor={`place-${icon}`}>{label}</label>
      <div className={`place-input-wrap ${focused ? 'is-focused' : ''}`}>
        <span className={`place-symbol ${icon}`} aria-hidden="true"><MapPin size={16} /></span>
        <input
          id={`place-${icon}`}
          value={query}
          onChange={(event) => { setQuery(event.target.value); onChange(event.target.value) }}
          onFocus={() => setFocused(true)}
          onBlur={() => window.setTimeout(() => setFocused(false), 160)}
          placeholder={placeholder}
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={showList}
          aria-controls={`suggestions-${icon}`}
        />
        {query && <button className="clear-input" type="button" aria-label={`Clear ${label}`} onMouseDown={(e) => e.preventDefault()} onClick={() => { setQuery(''); onChange('') }}><X size={14} /></button>}
        {showList && (
          <div className="suggestions" id={`suggestions-${icon}`} role="listbox">
            {results.isFetching && <div className="suggestion-note"><Search size={14} /> Searching places…</div>}
            {results.isError && <div className="suggestion-note error-note">{results.error.message}</div>}
            {results.data?.map((place) => (
              <button key={`${place.lat}-${place.lon}-${place.label}`} type="button" role="option" className="suggestion-item" onMouseDown={(e) => e.preventDefault()} onClick={() => { onSelect(place); setQuery(place.label); setFocused(false) }}>
                <MapPin size={15} /><span>{place.label}</span>
              </button>
            ))}
            {!results.isFetching && !results.isError && results.data?.length === 0 && <div className="suggestion-note">No matching places found.</div>}
          </div>
        )}
      </div>
    </div>
  )
}
