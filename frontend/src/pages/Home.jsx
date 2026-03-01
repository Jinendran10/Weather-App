import React, { useState, useEffect, useRef } from 'react'
import SearchBar from '../components/SearchBar'
import WeatherCard from '../components/WeatherCard'
import MapView from '../components/MapView'
import YouTubePanel from '../components/YouTubePanel'
import { weatherApi, integrationsApi } from '../services/api'
import { Cloud, Map, Youtube, AlertTriangle } from 'lucide-react'

/**
 * Home page – live current weather lookup.
 *
 * State management rules (req #1 – #6):
 *   - Each section owns its own dedicated state triple: data / error / loading.
 *     No section's state is ever shared with or can overwrite another's.
 *   - hasSearched is set to true on the first search and NEVER reset to false.
 *     The YouTube container is therefore ALWAYS in the DOM after a first search
 *     regardless of API success, failure, or null data (req #6).
 *   - All three API calls fire in parallel via Promise.allSettled; each result
 *     is settled independently.  A failure in weather or map CANNOT affect the
 *     YouTube section (req #2).
 *   - The `searchId` ref prevents stale async callbacks: if the user fires a
 *     second search before the first one completes, the first one's setState
 *     calls are silently dropped (req #5).
 *   - Loading flags are separate: weatherLoading / mapLoading / videoLoading
 *     (req #3).
 */
export default function Home() {
  // ── req #3 – three independent loading flags ──────────────────────────────
  const [weather, setWeather]           = useState(null)
  const [weatherError, setWeatherError] = useState(null)
  const [loadingWeather, setLoadingWeather] = useState(false)

  const [mapData, setMapData]     = useState(null)
  const [loadingMap, setLoadingMap] = useState(false)

  // videoLoading is the dedicated flag for the YouTube section only.
  // It is never set by weather or map code paths (req #3).
  const [ytData, setYtData]       = useState(null)
  const [ytError, setYtError]     = useState(null)
  const [loadingYt, setLoadingYt] = useState(false)

  // ── req #2 / #6 – gate: shown once, never hidden again ───────────────────
  // hasSearched controls whether the three sections are VISIBLE at all.
  // It transitions false → true on the first search and is never reset.
  const [hasSearched, setHasSearched] = useState(false)

  // ── req #5 – prevent stale async callbacks ───────────────────────────────
  // Each call to handleSearch increments this counter.  Before any setState
  // call after the await we compare against the current counter; if they
  // differ the result belongs to a superseded search and is discarded.
  const searchIdRef = useRef(0)

  // ── req #4 – log ytData every time it changes ────────────────────────────
  useEffect(() => {
    console.debug('[Home] ytData changed →', ytData)
  }, [ytData])

  const handleSearch = async (location) => {
    // 1. Stamp this search so stale callbacks from a previous call are ignored.
    searchIdRef.current += 1
    const myId = searchIdRef.current

    // 2. Mark that a search was attempted so all three sections become visible.
    //    This flag is only ever set to true; it is never reset.
    setHasSearched(true)

    // 3. Reset per-section state independently – never combined (req #1).
    setWeather(null)
    setWeatherError(null)
    setLoadingWeather(true)

    setMapData(null)
    setLoadingMap(true)

    // videoLoading resets independently – weather/map flags have no effect (req #3).
    setYtData(null)
    setYtError(null)
    setLoadingYt(true)

    console.debug('[Home] Firing 3 parallel API calls for:', location, '| searchId:', myId)

    // 3. All three calls fire at the same time; we wait for ALL of them
    const [wRes, mRes, yRes] = await Promise.allSettled([
      weatherApi.getCurrentWeather(location),
      integrationsApi.getMapsForLocation(location),
      integrationsApi.getYoutubeForLocation(location),
    ])

    // 4. Drop this result if the user already fired a newer search (req #5).
    if (searchIdRef.current !== myId) {
      console.debug('[Home] Dropping stale response for searchId:', myId)
      return
    }

    // 5. Settle each section independently – failure in one never affects another.
    //    All setState calls below are batched by React 18 into one re-render.
    // ── weatherLoading ────────────────────────────────────────────────────────
    setLoadingWeather(false)
    if (wRes.status === 'fulfilled') {
      const data = wRes.value
      console.log('[Home] Weather response:', data)
      if (data?.detail || data?.error) {
        setWeatherError(data.detail || data.error)
      } else {
        setWeather(data)
      }
    } else {
      const msg =
        wRes.reason?.response?.data?.detail ||
        wRes.reason?.message ||
        'Failed to fetch weather data.'
      console.error('[Home] Weather error:', msg)
      setWeatherError(msg)
    }

    // ── mapLoading ────────────────────────────────────────────────────────────
    setLoadingMap(false)
    if (mRes.status === 'fulfilled') {
      console.log('[Home] Maps response:', mRes.value)
      setMapData(mRes.value ?? null)
    } else {
      console.warn('[Home] Maps API failed – map hidden:', mRes.reason?.message)
      // mapData stays null, section hides itself (map failure is non-critical)
    }

    // ── videoLoading (req #3) ─────────────────────────────────────────────────
    // Cleared regardless of outcome so the YouTube container always exits the
    // loading skeleton and renders its stable outer div (req #6).
    setLoadingYt(false)
    if (yRes.status === 'fulfilled') {
      const data = yRes.value
      console.log('[Home] YouTube response:', data)
      // data should be { location: string, youtube: { search_url, query } }
      if (data?.youtube?.search_url) {
        setYtData(data)
        console.debug('[Home] YouTube search URL set:', data.youtube.search_url)
      } else if (data?.detail || data?.error) {
        const msg = data.detail || data.error
        console.warn('[Home] YouTube API returned error payload:', msg)
        setYtError(msg)
      } else {
        // Response present but no search_url – treat as soft failure
        console.warn('[Home] YouTube response missing search_url:', data)
        setYtError('YouTube unavailable for this location.')
      }
    } else {
      const msg =
        yRes.reason?.response?.data?.detail ||
        yRes.reason?.message ||
        'Failed to load YouTube content.'
      console.error('[Home] YouTube error:', msg)
      setYtError(msg)
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

      {/* ── Weather – independent visibility ─────────────────────────────── */}
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

      {/* ── Map – independent visibility ─────────────────────────────────── */}
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

      {/* ── YouTube – ALWAYS rendered after first search (req #2, #6) ──────────
           Gate: hasSearched ONLY.  Not gated on ytData, weather, or mapData.
           The section can never disappear because hasSearched never goes back
           to false.  Inside, videoLoading / ytError / ytData are independent
           of the other two sections' state (req #3).                           */}
      {hasSearched && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-500 uppercase tracking-widest">
            <Youtube className="w-4 h-4 text-red-500" /> Explore on YouTube
          </h2>

          {/* videoLoading skeleton – driven by its own flag, not by weather/map */}
          {loadingYt ? (
            <div className="card overflow-hidden animate-pulse">
              <div className="bg-slate-200 w-full aspect-video" />
              <div className="p-4 space-y-2">
                <div className="h-4 bg-slate-200 rounded w-1/2" />
                <div className="h-3 bg-slate-200 rounded w-1/3" />
              </div>
            </div>

          /* Explicit error state — not gated on weather or map (req #2) */
          ) : ytError ? (
            <div className="card p-6 flex items-start gap-3 border-amber-200 bg-amber-50">
              <Youtube className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-amber-800 font-semibold text-sm">YouTube unavailable</p>
                <p className="text-amber-700 text-sm mt-0.5">{ytError}</p>
              </div>
            </div>

          /* YouTubePanel always renders its outer container (req #6);
             when ytData is null it shows a fallback, never a blank space. */
          ) : (
            <YouTubePanel data={ytData} loading={false} />
          )}
        </section>
      )}
    </div>
  )
}
