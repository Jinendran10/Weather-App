import React, { useEffect } from 'react'
import { Youtube, ExternalLink, MapPin } from 'lucide-react'

/**
 * YouTubePanel — "Watch Travel Videos" button component.
 *
 * Design contract:
 *   - NO iframe, NO embed, NO API key required.
 *   - Opens https://www.youtube.com/results?search_query=<query> in a new tab.
 *   - Container is ALWAYS rendered after first search (independent of weather/map).
 *   - Button is disabled only when location is empty/null.
 *   - Shows a friendly message when no location is available.
 *
 * Props:
 *   data     — { location: string, youtube: { search_url: string, query: string } }
 *   loading  — videoLoading flag (independent of weatherLoading / mapLoading)
 */
export default function YouTubePanel({ data, loading = false }) {
  // ── Lifecycle / debug logging ─────────────────────────────────────────────
  useEffect(() => {
    console.debug('[YouTubePanel] mounted')
    return () => console.debug('[YouTubePanel] unmounted')
  }, [])

  useEffect(() => {
    const url = data?.youtube?.search_url ?? null
    console.debug('[YouTubePanel] data changed →', {
      location:  data?.location ?? null,
      searchUrl: url,
      query:     data?.youtube?.query ?? null,
    })
  }, [data])

  // ── Derived values ────────────────────────────────────────────────────────
  const rawLocation = typeof data?.location === 'string' ? data.location.trim() : ''
  const searchUrl   = data?.youtube?.search_url ?? null
  const query       = data?.youtube?.query       ?? null

  // Validate: must have a non-empty location and a well-formed search URL
  const isValid = Boolean(rawLocation && searchUrl && searchUrl.startsWith('https://'))

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (loading) {
    return (
      <div
        className="card p-6 animate-pulse"
        style={{ backgroundColor: 'var(--card, #FFFFFF)' }}
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-full bg-slate-200" />
          <div className="h-4 bg-slate-200 rounded w-40" />
        </div>
        <div className="h-12 bg-slate-200 rounded-xl w-full" />
      </div>
    )
  }

  // ── Stable container — ALWAYS rendered, never hidden by other sections ────
  return (
    <div
      className="card p-6 space-y-4"
      style={{ backgroundColor: 'var(--card, #FFFFFF)' }}
    >
      {/* Header row */}
      <div className="flex items-center gap-3">
        <div
          className="flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center"
          style={{ backgroundColor: '#EF44441A' }}
        >
          <Youtube className="w-5 h-5" style={{ color: '#EF4444' }} />
        </div>
        <div>
          <h3
            className="font-semibold text-sm leading-tight"
            style={{ color: 'var(--text-main, #0F172A)' }}
          >
            Explore on YouTube
          </h3>
          {query && (
            <p
              className="text-xs mt-0.5 truncate max-w-xs"
              style={{ color: 'var(--text-secondary, #475569)' }}
            >
              {query}
            </p>
          )}
        </div>
      </div>

      {/* Location pill */}
      {rawLocation && (
        <div className="flex items-center gap-1.5">
          <MapPin
            className="w-3.5 h-3.5 flex-shrink-0"
            style={{ color: 'var(--text-secondary, #475569)' }}
          />
          <span
            className="text-xs truncate"
            style={{ color: 'var(--text-secondary, #475569)' }}
          >
            {rawLocation}
          </span>
        </div>
      )}

      {/* Primary button — opens YouTube search in a new tab */}
      {isValid ? (
        <a
          href={searchUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="
            group flex items-center justify-center gap-2
            w-full px-5 py-3 rounded-xl
            font-semibold text-sm text-white
            transition-all duration-200 ease-in-out
            focus:outline-none focus:ring-2 focus:ring-offset-2
          "
          style={{
            backgroundColor: 'var(--primary, #2563EB)',
            '--tw-ring-color': 'var(--primary, #2563EB)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--secondary, #38BDF8)'
            e.currentTarget.style.color = 'var(--text-main, #0F172A)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'var(--primary, #2563EB)'
            e.currentTarget.style.color = '#FFFFFF'
          }}
          aria-label={`Watch travel videos for ${rawLocation} on YouTube`}
        >
          <Youtube className="w-4 h-4 flex-shrink-0" />
          Watch Travel Videos
          <ExternalLink className="w-3.5 h-3.5 flex-shrink-0 opacity-70" />
        </a>
      ) : (
        /* Fallback when location is invalid / null — never blank, never crashes */
        <div
          className="w-full px-5 py-3 rounded-xl text-sm text-center select-none"
          style={{
            backgroundColor: 'var(--bg, #F1F5F9)',
            color: 'var(--text-secondary, #475569)',
          }}
        >
          {data?.detail || data?.error
            ? `YouTube unavailable: ${data.detail || data.error}`
            : 'Enter a location to find travel videos.'}
        </div>
      )}

      {/* Subtle hint text */}
      {isValid && (
        <p
          className="text-xs text-center"
          style={{ color: 'var(--text-secondary, #475569)' }}
        >
          Opens YouTube search results in a new tab
        </p>
      )}
    </div>
  )
}

