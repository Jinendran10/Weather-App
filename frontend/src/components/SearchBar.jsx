import React, { useState } from 'react'
import { Search, MapPin, Loader2 } from 'lucide-react'

/**
 * SearchBar – allows user to type any location (city, ZIP, GPS coords, landmark)
 * and triggers a search callback.
 */
export default function SearchBar({ onSearch, loading = false, placeholder }) {
  const [value, setValue] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = value.trim()
    if (trimmed) onSearch(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={
            placeholder ||
            'Enter city, ZIP code, GPS coordinates, or landmark…'
          }
          className="input pl-10"
          disabled={loading}
        />
      </div>
      <button type="submit" className="btn-primary flex items-center gap-2" disabled={loading || !value.trim()}>
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Search className="w-4 h-4" />
        )}
        Search
      </button>
    </form>
  )
}
