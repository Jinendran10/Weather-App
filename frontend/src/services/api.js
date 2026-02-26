/**
 * Centralized API client using Axios.
 * All backend calls are routed through /api/v1 via Vite proxy.
 */

import axios from 'axios'
import toast from 'react-hot-toast'

const BASE_URL = '/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Global error interceptor
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.error ||
      err.message ||
      'An unexpected error occurred.'
    // Don't toast on 404 (handled per-component)
    if (err.response?.status !== 404) {
      toast.error(msg)
    }
    return Promise.reject(err)
  }
)

// ── Weather CRUD ──────────────────────────────────────────────────────────────

export const weatherApi = {
  /** GET live current weather (not persisted) */
  getCurrentWeather: (rawInput) =>
    api.post('/weather/current', { raw_input: rawInput }).then((r) => r.data),

  /** CREATE – Submit a date-range query */
  createQuery: (payload) =>
    api.post('/weather/queries', payload).then((r) => r.data),

  /** READ – List all queries */
  listQueries: (params = {}) =>
    api.get('/weather/queries', { params }).then((r) => r.data),

  /** READ – Get single query with records */
  getQuery: (id) =>
    api.get(`/weather/queries/${id}`).then((r) => r.data),

  /** UPDATE – Edit query metadata */
  updateQuery: (id, payload) =>
    api.patch(`/weather/queries/${id}`, payload).then((r) => r.data),

  /** DELETE – Remove query + records */
  deleteQuery: (id) =>
    api.delete(`/weather/queries/${id}`).then((r) => r.data),

  /** UPDATE – Correct a daily record */
  updateRecord: (id, payload) =>
    api.patch(`/weather/records/${id}`, payload).then((r) => r.data),

  /** DELETE – Remove a daily record */
  deleteRecord: (id) =>
    api.delete(`/weather/records/${id}`).then((r) => r.data),
}

// ── Integrations ──────────────────────────────────────────────────────────────

export const integrationsApi = {
  getMapsForLocation: (location, zoom = 12) =>
    api
      .get('/integrations/maps/location', { params: { location, zoom } })
      .then((r) => r.data),

  getYoutubeForLocation: (location, maxResults = 6) =>
    api
      .get('/integrations/youtube/location', {
        params: { location, max_results: maxResults },
      })
      .then((r) => r.data),

  getMapsForQuery: (queryId, zoom = 12) =>
    api
      .get(`/integrations/maps/query/${queryId}`, { params: { zoom } })
      .then((r) => r.data),

  getYoutubeForQuery: (queryId, maxResults = 6) =>
    api
      .get(`/integrations/youtube/query/${queryId}`, {
        params: { max_results: maxResults },
      })
      .then((r) => r.data),
}

// ── Export ────────────────────────────────────────────────────────────────────

export const exportApi = {
  exportData: async (payload) => {
    const response = await api.post('/export', payload, {
      responseType: 'blob',
    })
    const ext = payload.format === 'json' ? 'json' : 'csv'
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `weather_export.${ext}`
    a.click()
    URL.revokeObjectURL(url)
  },
}
