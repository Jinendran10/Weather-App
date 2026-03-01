import React, { useState } from 'react'
import SearchBar from '../components/SearchBar'
import WeatherCard from '../components/WeatherCard'
import MapView from '../components/MapView'
import YouTubePanel from '../components/YouTubePanel'
import { weatherApi, integrationsApi } from '../services/api'
import { Cloud, Map, Youtube, AlertTriangle } from 'lucide-react'

/**
 * Home page – live current weather lookup.
 *
 * Defensive rules applied:
 *   - Every API call result is checked before use
 *   - Error state shown inline per section (never crashes whole page)
 *   - Console logs for every API response to aid debugging
 *   - No property access without existence check
 */
export default function Home() {
  const [weather, setWeather] = useState(null)
  const [weatherError, setWeatherError] = useState(null)
  const [mapData, setMapData] = useState(null)
  const [ytData, setYtData] = useState(null)
  const [loadingWeather, setLoadingWeather] = useState(false)
  const [loadingMap, setLoadingMap] = useState(false)
  const [loadingYt, setLoadingYt] = useState(false)

  const handleSearch = async (location) => {
    // Reset all state on every new search
    setWeather(null)
    setWeatherError(null)
    setMapData(null)
    setYtData(null)

    setLoadingWeather(true)
    setLoadingMap(true)
    setLoadingYt(true)

    const [wRes, mRes, yRes] = await Promise.allSettled([
      weatherApi.getCurrentWeather(location),
      integrationsApi.getMapsForLocation(location),
      integrationsApi.getYoutubeForLocation(location),
    ])

    // ── Weather ──────────────────────────────────────────────────────────────
    setLoadingWeather(false)
    if (wRes.status === 'fulfilled') {
      const data = wRes.value
      console.log('[Home] Weather API response:', data)
      // Guard: backend may return an error object instead of valid weather
      if (data && typeof data.temp_celsius === 'number') {
        setWeather(data)
      } else if (data?.detail || data?.error) {
        const msg = data.detail || data.error
        console.warn('[Home] Weather API returned error payload:', msg)
        setWeatherError(msg)
      } else {
        setWeather(data)
      }
    } else {
      const errMsg =
        wRes.reason?.response?.data?.detail ||
        wRes.reason?.response?.data?.error ||
        wRes.reason?.message ||
        'Failed to fetch weather data.'
      console.error('[Home] Weather API error:', errMsg, wRes.reason)
      setWeatherError(errMsg)
    }

    // ── Map ───────────────────────────────────────────────────────────────────
    setLoadingMap(false)
    if (mRes.status === 'fulfilled') {
      console.log('[Home] Maps API response:', mRes.value)
      setMapData(mRes.value ?? null)
    } else {
      console.warn('[Home] Maps API failed (map hidden):', mRes.reason?.message)
    }

    // ── YouTube ───────────────────────────────────────────────────────────────
    setLoadingYt(false)
    if (yRes.status === 'fulfilled') {
      console.log('[Home] YouTube API response:', yRes.value)
      setYtData(yRes.value ?? null)
    } else {
      console.warn('[Home] YouTube API failed (panel hidden):', yRes.reason?.message)
    }
  }

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="text-center space-y-3 py-8">
        <h1 className="text-4xl font-bold text-text-main tracking-tight">
          <span className="text-primary">Weather</span>Vault
        </h1>
        <p className="text-text-sec max-w-xl mx-auto">
          Real-time weather intelligence for any location on earth.
          Enter a city, ZIP code, GPS coordinates, or landmark.
        </p>
      </div>

      {/* Search */}
      <SearchBar onSearch={handleSearch} loading={loadingWeather} />

      {/* Current weather */}
      {(loadingWeather || weather || weatherError) && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-widest">
            <Cloud className="w-4 h-4" /> Current Conditions
          </h2>
          {loadingWeather ? (
            <div className="card p-8 text-center text-slate-400 animate-pulse">Fetching weather…</div>
          ) : weatherError ? (
            <div className="card p-6 flex items-start gap-3 border-red-200 bg-red-50">
              <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-700 font-semibold text-sm">Could not load weather</p>
                <p className="text-red-600 text-sm mt-0.5">{weatherError}</p>
              </div>
            </div>
          ) : (
            <WeatherCard data={weather} title="Current Weather" />
          )}
        </section>
      )}

      {/* Map */}
      {(loadingMap || mapData) && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-widest">
            <Map className="w-4 h-4" /> Location Map
          </h2>
          {loadingMap ? (
            <div className="card h-64 animate-pulse bg-slate-100" />
          ) : (mapData?.latitude && mapData?.longitude) ? (
            <MapView
              latitude={mapData.latitude}
              longitude={mapData.longitude}
              locationName={mapData.location}
              height="320px"
            />
          ) : null}
        </section>
      )}

      {/* YouTube */}
      {(loadingYt || ytData) && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-widest">
            <Youtube className="w-4 h-4 text-red-500" /> Explore on YouTube
          </h2>
          <YouTubePanel data={ytData} loading={loadingYt} />
        </section>
      )}
    </div>
  )
}

