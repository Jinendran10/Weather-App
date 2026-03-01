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

// ── Request interceptor: log every outgoing call ──────────────────────────────
api.interceptors.request.use((config) => {
  console.debug(`[API] ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`,
    config.params || config.data || '')
  return config
})

// ── Response interceptor: log + surface errors ────────────────────────────────
api.interceptors.response.use(
  (res) => {
    console.debug(`[API] ← ${res.status} ${res.config.url}`, res.data)
    return res
  },
  (err) => {
    const status = err.response?.status
    const responseData = err.response?.data

    // Log full error data so developers can see exactly what came back
    console.error('[API] Error', {
      url: err.config?.url,
      status,
      data: responseData,
      message: err.message,
    })

    const msg =
      responseData?.detail ||
      responseData?.error ||
      err.message ||
      'An unexpected error occurred.'

    // Don't toast on 404 (handled per-component) or 401 (shown inline)
    if (status !== 404 && status !== 401) {
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
