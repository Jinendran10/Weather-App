import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { weatherApi, integrationsApi } from '../services/api'
import WeatherCard from '../components/WeatherCard'
import MapView from '../components/MapView'
import YouTubePanel from '../components/YouTubePanel'
import ExportButtons from '../components/ExportButtons'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend, BarChart, Bar
} from 'recharts'
import {
  ArrowLeft, Trash2, Pencil, MapPin, Calendar, Tag,
  Thermometer, BarChart2, Cloud, Map, Youtube, AlertTriangle
} from 'lucide-react'
import toast from 'react-hot-toast'

function RecordRow({ record, onDelete }) {
  return (
    <tr className="border-b border-slate-700/40 hover:bg-slate-800/30 transition-colors">
      <td className="py-2.5 px-3 text-slate-300 font-mono text-sm">{record.record_date}</td>
      <td className="py-2.5 px-3 text-blue-300">{record.temp_min?.toFixed(1) ?? '—'}</td>
      <td className="py-2.5 px-3 text-orange-300">{record.temp_max?.toFixed(1) ?? '—'}</td>
      <td className="py-2.5 px-3 text-white">{record.temp_avg?.toFixed(1) ?? '—'}</td>
      <td className="py-2.5 px-3 text-slate-400">{record.humidity ?? '—'}%</td>
      <td className="py-2.5 px-3 text-slate-400">{record.wind_speed?.toFixed(1) ?? '—'}</td>
      <td className="py-2.5 px-3 text-slate-400 max-w-xs truncate capitalize">{record.weather_description ?? '—'}</td>
      <td className="py-2.5 px-3">
        <button
          onClick={() => onDelete(record.id)}
          className="text-red-400/60 hover:text-red-400 transition-colors"
          title="Delete this record"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </td>
    </tr>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-800 border border-slate-600 rounded-xl p-3 text-sm shadow-xl">
        <p className="text-slate-400 mb-1">{label}</p>
        {payload.map((p) => (
          <p key={p.name} style={{ color: p.color }}>
            {p.name}: <strong>{p.value?.toFixed?.(1) ?? p.value}</strong>
          </p>
        ))}
      </div>
    )
  }
  return null
}

/**
 * QueryDetail page – shows full query with charts, map, YouTube, CRUD on records.
 */
export default function QueryDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState(null)
  const [mapData, setMapData] = useState(null)
  const [ytData, setYtData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [activeTab, setActiveTab] = useState('chart')

  const load = async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const q = await weatherApi.getQuery(id)
      console.log('[QueryDetail] Query data:', q)
      setQuery(q)
      const [mRes, yRes] = await Promise.allSettled([
        integrationsApi.getMapsForQuery(id),
        integrationsApi.getYoutubeForQuery(id),
      ])
      if (mRes.status === 'fulfilled') setMapData(mRes.value)
      if (yRes.status === 'fulfilled') {
        console.log('[QueryDetail] YouTube data:', yRes.value)
        setYtData(yRes.value)
      }
    } catch (err) {
      const status = err.response?.status
      if (status === 404) {
        toast.error('Query not found.')
        navigate('/history')
      } else {
        const msg = err.response?.data?.detail || err.message || 'Failed to load query.'
        console.error('[QueryDetail] Load error:', msg)
        setLoadError(msg)
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [id])

  const handleDeleteRecord = async (recordId) => {
    if (!window.confirm('Delete this daily record?')) return
    await toast.promise(weatherApi.deleteRecord(recordId), {
      loading: 'Deleting record…', success: 'Record deleted.', error: 'Failed.',
    })
    load()
  }

  const handleDeleteQuery = async () => {
    if (!window.confirm('Delete this entire query and all its records?')) return
    await toast.promise(weatherApi.deleteQuery(id), {
      loading: 'Deleting…', success: 'Query deleted.', error: 'Failed.',
    })
    navigate('/history')
  }

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-slate-800 rounded-xl w-1/3" />
        <div className="h-64 bg-slate-800 rounded-2xl" />
        <div className="h-48 bg-slate-800 rounded-2xl" />
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="card p-8 flex flex-col items-center gap-4 text-center">
        <AlertTriangle className="w-10 h-10 text-red-400 opacity-70" />
        <p className="text-red-300 font-semibold">Failed to load query</p>
        <p className="text-slate-400 text-sm">{loadError}</p>
        <button className="btn-secondary" onClick={() => navigate('/history')}>Back to History</button>
      </div>
    )
  }

  if (!query) return null

  // Guard: weather_records may be null/undefined if query is malformed
  const sortedRecords = Array.isArray(query.weather_records)
    ? [...query.weather_records].sort(
        (a, b) => new Date(a.record_date) - new Date(b.record_date)
      )
    : []

  const chartData = sortedRecords.map((r) => ({
    date: r.record_date,
    'Min °C': r.temp_min,
    'Max °C': r.temp_max,
    'Avg °C': r.temp_avg,
    Humidity: r.humidity,
    'Wind m/s': r.wind_speed,
    'Rain mm': r.precipitation,
  }))

  const TABS = [
    { id: 'chart', icon: BarChart2, label: 'Charts' },
    { id: 'table', icon: Thermometer, label: 'Records' },
    { id: 'map', icon: Map, label: 'Map' },
    { id: 'youtube', icon: Youtube, label: 'Videos' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <button
            onClick={() => navigate('/history')}
            className="flex items-center gap-1 text-slate-400 hover:text-white text-sm mb-2 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to History
          </button>
          <h1 className="text-2xl font-bold text-white">
            {query.label || query.location?.resolved_name || 'Query Detail'}
          </h1>
          <div className="flex items-center gap-4 mt-1.5 text-sm text-slate-400 flex-wrap">
            <span className="flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" /> {query.location?.resolved_name ?? 'Unknown location'}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="w-3.5 h-3.5" />
              {query.date_from} → {query.date_to}
            </span>
            {query.label && (
              <span className="flex items-center gap-1">
                <Tag className="w-3.5 h-3.5" /> {query.label}
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ExportButtons queryIds={[id]} label="Export" />
          <button className="btn-danger flex items-center gap-1.5" onClick={handleDeleteQuery}>
            <Trash2 className="w-4 h-4" /> Delete Query
          </button>
        </div>
      </div>

      {/* Summary cards */}
      {sortedRecords.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[
            {
              label: 'Avg Temp',
              value: sortedRecords.length > 0
                ? (() => {
                    const avg = sortedRecords.reduce((s, r) => s + (r.temp_avg ?? 0), 0) / sortedRecords.length
                    return isFinite(avg) ? avg.toFixed(1) + '°C' : '—'
                  })()
                : '—',
            },
            {
              label: 'Max Temp',
              value: sortedRecords.length > 0
                ? (() => {
                    const vals = sortedRecords.map((r) => r.temp_max).filter((v) => v != null)
                    return vals.length > 0 ? Math.max(...vals).toFixed(1) + '°C' : '—'
                  })()
                : '—',
            },
            {
              label: 'Min Temp',
              value: sortedRecords.length > 0
                ? (() => {
                    const vals = sortedRecords.map((r) => r.temp_min).filter((v) => v != null)
                    return vals.length > 0 ? Math.min(...vals).toFixed(1) + '°C' : '—'
                  })()
                : '—',
            },
            {
              label: 'Records',
              value: sortedRecords.length,
            },
          ].map((s) => (
            <div key={s.label} className="stat-card">
              <p className="text-xs text-slate-500 uppercase tracking-widest">{s.label}</p>
              <p className="text-2xl font-bold text-white">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Notes */}
      {query.notes && (
        <div className="card p-4 flex items-start gap-3">
          <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-slate-300">{query.notes}</p>
        </div>
      )}

      {/* Tab nav */}
      <div className="flex gap-1 bg-slate-800/60 rounded-xl p-1 w-fit">
        {TABS.map((t) => {
          const Icon = t.icon
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === t.id
                  ? 'bg-sky-500 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {t.label}
            </button>
          )
        })}
      </div>

      {/* Tab: Charts */}
      {activeTab === 'chart' && chartData.length > 0 && (
        <div className="space-y-4">
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-4">
              Temperature Over Time
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 11 }} unit="°C" />
                <Tooltip content={<CustomTooltip />} />
                <Legend wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="Min °C" stroke="#60a5fa" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Avg °C" stroke="#f0f9ff" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="Max °C" stroke="#fb923c" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-4">
                Humidity (%)
              </h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} unit="%" />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="Humidity" fill="#38bdf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-widest mb-4">
                Precipitation (mm)
              </h3>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                  <YAxis tick={{ fill: '#94a3b8', fontSize: 10 }} unit="mm" />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="Rain mm" fill="#818cf8" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'chart' && chartData.length === 0 && (
        <div className="card p-8 text-center text-slate-500">
          <BarChart2 className="w-8 h-8 mx-auto mb-2 opacity-30" />
          No weather records to chart.
        </div>
      )}

      {/* Tab: Table */}
      {activeTab === 'table' && (
        <div className="card overflow-hidden">
          {sortedRecords.length === 0 ? (
            <div className="p-8 text-center text-slate-500">No records available.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-800/80">
                  <tr>
                    {['Date', 'Min °C', 'Max °C', 'Avg °C', 'Humidity', 'Wind m/s', 'Conditions', ''].map((h) => (
                      <th key={h} className="py-3 px-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-widest">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sortedRecords.map((r) => (
                    <RecordRow key={r.id} record={r} onDelete={handleDeleteRecord} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Map */}
      {activeTab === 'map' && (
        (query.location?.latitude && query.location?.longitude) ? (
          <MapView
            latitude={query.location.latitude}
            longitude={query.location.longitude}
            locationName={query.location?.resolved_name}
            height="420px"
          />
        ) : (
          <div className="card p-8 text-center text-slate-500">Location coordinates unavailable.</div>
        )
      )}

      {/* Tab: YouTube */}
      {activeTab === 'youtube' && (
        <YouTubePanel data={ytData} loading={false} />
      )}
    </div>
  )
}
