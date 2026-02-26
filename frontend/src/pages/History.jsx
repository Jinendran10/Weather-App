import React, { useState, useEffect, useCallback } from 'react'
import DateRangeForm from '../components/DateRangeForm'
import WeatherHistory from '../components/WeatherHistory'
import ExportButtons from '../components/ExportButtons'
import { weatherApi } from '../services/api'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'
import { Database, Plus, X } from 'lucide-react'

/**
 * History page – full CRUD interface.
 * CREATE via form, READ list, navigate to detail for UPDATE/DELETE.
 */
export default function History() {
  const [queries, setQueries] = useState([])
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  const loadQueries = useCallback(async () => {
    setLoading(true)
    try {
      const data = await weatherApi.listQueries({
        limit: 50,
        location_search: search || undefined,
      })
      setQueries(data)
    } finally {
      setLoading(false)
    }
  }, [search])

  useEffect(() => {
    loadQueries()
  }, [loadQueries])

  const handleCreate = async (payload) => {
    setSubmitting(true)
    try {
      await toast.promise(weatherApi.createQuery(payload), {
        loading: 'Fetching & saving weather data…',
        success: 'Query saved successfully!',
        error: (err) => err.response?.data?.detail || 'Failed to create query.',
      })
      setShowForm(false)
      loadQueries()
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Database className="w-6 h-6 text-sky-400" />
            Weather History
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Create, browse, update and delete weather queries with date ranges.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <ExportButtons label="Export All" />
          <button
            className="btn-primary flex items-center gap-2"
            onClick={() => setShowForm((v) => !v)}
          >
            {showForm ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            {showForm ? 'Cancel' : 'New Query'}
          </button>
        </div>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card p-6">
          <h2 className="font-semibold text-white mb-4">New Weather Query</h2>
          <DateRangeForm onSubmit={handleCreate} loading={submitting} />
        </div>
      )}

      {/* Search filter */}
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Filter by location name…"
        className="input max-w-sm"
      />

      {/* List */}
      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="card h-20 animate-pulse" />
          ))}
        </div>
      ) : (
        <WeatherHistory
          queries={queries}
          onRefresh={loadQueries}
          onViewQuery={(id) => navigate(`/query/${id}`)}
        />
      )}
    </div>
  )
}
