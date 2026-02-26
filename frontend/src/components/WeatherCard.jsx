import React from 'react'
import {
  Thermometer, Droplets, Wind, Eye, Gauge, Sun, Sunrise, Sunset,
  Cloud, Snowflake, CloudRain, Navigation
} from 'lucide-react'

const ICON_MAP = {
  '01d': '☀️', '01n': '🌙', '02d': '⛅', '02n': '⛅',
  '03d': '☁️', '03n': '☁️', '04d': '☁️', '04n': '☁️',
  '09d': '🌧️', '09n': '🌧️', '10d': '🌦️', '10n': '🌧️',
  '11d': '⛈️', '11n': '⛈️', '13d': '❄️', '13n': '❄️',
  '50d': '🌫️', '50n': '🌫️',
}

function StatPill({ icon: Icon, label, value, unit }) {
  return (
    <div className="flex items-center gap-2 bg-slate-800/60 rounded-xl px-4 py-2.5">
      <Icon className="w-4 h-4 text-sky-400 flex-shrink-0" />
      <div>
        <p className="text-xs text-slate-400">{label}</p>
        <p className="text-sm font-semibold text-white">
          {value ?? '—'}{unit && <span className="text-slate-400 text-xs ml-0.5">{unit}</span>}
        </p>
      </div>
    </div>
  )
}

/**
 * WeatherCard – displays current or daily weather data.
 */
export default function WeatherCard({ data, title = 'Current Weather' }) {
  if (!data) return null

  const emoji = ICON_MAP[data.weather_icon] || '🌡️'
  const tempC = data.temp_celsius ?? data.temp_avg
  const tempF = data.temp_fahrenheit ?? (tempC != null ? (tempC * 9) / 5 + 32 : null)

  const fmt = (dt) => {
    if (!dt) return '—'
    try {
      return new Date(dt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    } catch {
      return '—'
    }
  }

  return (
    <div className="card p-6 space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-lg font-bold text-white">{title}</h2>
          {data.location && (
            <p className="text-sm text-slate-400 mt-0.5 flex items-center gap-1">
              <Navigation className="w-3.5 h-3.5" />
              {data.location.resolved_name}
            </p>
          )}
          {data.record_date && (
            <p className="text-xs text-slate-500 mt-0.5">{data.record_date}</p>
          )}
        </div>
        <span className="text-5xl">{emoji}</span>
      </div>

      {/* Temperature */}
      <div className="flex items-end gap-4">
        <span className="text-6xl font-bold text-white">
          {tempC != null ? `${tempC.toFixed(1)}°C` : '—'}
        </span>
        <span className="text-2xl text-slate-400 mb-2">
          {tempF != null ? `${tempF.toFixed(1)}°F` : ''}
        </span>
      </div>

      {/* Description */}
      {data.weather_description && (
        <p className="text-slate-300 capitalize font-medium">{data.weather_description}</p>
      )}
      {data.weather_main && data.weather_description && (
        <p className="text-xs text-slate-500 uppercase tracking-widest">{data.weather_main}</p>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        <StatPill icon={Droplets} label="Humidity" value={data.humidity} unit="%" />
        <StatPill icon={Gauge} label="Pressure" value={data.pressure} unit=" hPa" />
        <StatPill icon={Wind} label="Wind" value={data.wind_speed} unit=" m/s" />
        <StatPill icon={Eye} label="Visibility" value={data.visibility != null ? `${(data.visibility / 1000).toFixed(1)}` : null} unit=" km" />
        <StatPill icon={Cloud} label="Cloud Cover" value={data.cloud_cover} unit="%" />
        <StatPill icon={Sun} label="UV Index" value={data.uv_index} />
        {data.feels_like_celsius != null && (
          <StatPill icon={Thermometer} label="Feels Like" value={data.feels_like_celsius?.toFixed(1)} unit="°C" />
        )}
        {data.precipitation != null && (
          <StatPill icon={CloudRain} label="Rain" value={data.precipitation} unit=" mm" />
        )}
        {data.snow != null && data.snow > 0 && (
          <StatPill icon={Snowflake} label="Snow" value={data.snow} unit=" mm" />
        )}
      </div>

      {/* Sunrise / Sunset */}
      {(data.sunrise || data.sunset) && (
        <div className="flex gap-4 pt-2 border-t border-slate-700/50">
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Sunrise className="w-4 h-4 text-amber-400" />
            {fmt(data.sunrise)}
          </div>
          <div className="flex items-center gap-2 text-sm text-slate-300">
            <Sunset className="w-4 h-4 text-orange-400" />
            {fmt(data.sunset)}
          </div>
        </div>
      )}
    </div>
  )
}
