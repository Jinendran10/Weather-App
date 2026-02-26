import React, { useState } from 'react'
import SearchBar from '../components/SearchBar'
import WeatherCard from '../components/WeatherCard'
import MapView from '../components/MapView'
import YouTubePanel from '../components/YouTubePanel'
import { weatherApi, integrationsApi } from '../services/api'
import { Cloud, Map, Youtube } from 'lucide-react'

/**
 * Home page – live current weather lookup.
 * Shows current conditions, map, and YouTube videos.
 */
export default function Home() {
  const [weather, setWeather] = useState(null)
  const [mapData, setMapData] = useState(null)
  const [ytData, setYtData] = useState(null)
  const [loadingWeather, setLoadingWeather] = useState(false)
  const [loadingMap, setLoadingMap] = useState(false)
  const [loadingYt, setLoadingYt] = useState(false)

  const handleSearch = async (location) => {
    setWeather(null)
    setMapData(null)
    setYtData(null)

    // Fetch weather + map + youtube in parallel
    setLoadingWeather(true)
    setLoadingMap(true)
    setLoadingYt(true)

    const [wRes, mRes, yRes] = await Promise.allSettled([
      weatherApi.getCurrentWeather(location),
      integrationsApi.getMapsForLocation(location),
      integrationsApi.getYoutubeForLocation(location),
    ])

    setLoadingWeather(false)
    setLoadingMap(false)
    setLoadingYt(false)

    if (wRes.status === 'fulfilled') setWeather(wRes.value)
    if (mRes.status === 'fulfilled') setMapData(mRes.value)
    if (yRes.status === 'fulfilled') setYtData(yRes.value)
  }

  return (
    <div className="space-y-8">
      {/* Hero */}
      <div className="text-center space-y-3 py-8">
        <h1 className="text-4xl font-bold text-white tracking-tight">
          <span className="text-sky-400">Weather</span>Vault
        </h1>
        <p className="text-slate-400 max-w-xl mx-auto">
          Real-time weather intelligence for any location on earth.
          Enter a city, ZIP code, GPS coordinates, or landmark.
        </p>
      </div>

      {/* Search */}
      <SearchBar onSearch={handleSearch} loading={loadingWeather} />

      {/* Current weather */}
      {(loadingWeather || weather) && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-400 uppercase tracking-widest">
            <Cloud className="w-4 h-4" /> Current Conditions
          </h2>
          {loadingWeather ? (
            <div className="card p-8 text-center text-slate-500 animate-pulse">Fetching weather…</div>
          ) : (
            <WeatherCard data={weather} title="Current Weather" />
          )}
        </section>
      )}

      {/* Map */}
      {(loadingMap || mapData) && (
        <section className="space-y-2">
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-400 uppercase tracking-widest">
            <Map className="w-4 h-4" /> Location Map
          </h2>
          {loadingMap ? (
            <div className="card h-64 animate-pulse bg-slate-800" />
          ) : mapData ? (
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
          <h2 className="flex items-center gap-2 text-sm font-semibold text-slate-400 uppercase tracking-widest">
            <Youtube className="w-4 h-4 text-red-400" /> Explore on YouTube
          </h2>
          <YouTubePanel data={ytData} loading={loadingYt} />
        </section>
      )}
    </div>
  )
}
