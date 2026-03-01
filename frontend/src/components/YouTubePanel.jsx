import React, { useState } from 'react'
import { Youtube, ExternalLink, Search } from 'lucide-react'

/**
 * YouTubePanel – embeds a YouTube search playlist for a location.
 *
 * Backend response shape (new embed-based format):
 *   { location: string, youtube: { embed_url: string, query: string } }
 *
 * Defensive rules applied:
 *   - Never accesses .length or nested props without guarding
 *   - Uses optional chaining (?.) throughout
 *   - Handles: null data, missing youtube field, missing embed_url,
 *     backend error objects ({ detail: "..." }), loading state
 */
export default function YouTubePanel({ data, loading = false }) {
  const [iframeError, setIframeError] = useState(false)

  // ── Loading skeleton ───────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="card overflow-hidden animate-pulse">
        <div className="bg-slate-700 w-full aspect-video" />
        <div className="p-4 space-y-2">
          <div className="h-4 bg-slate-700 rounded w-1/2" />
          <div className="h-3 bg-slate-700 rounded w-1/3" />
        </div>
      </div>
    )
  }

  // ── Guard: no data at all, or API returned an error object ─────────────────
  // Backend error responses look like { detail: "..." } or { error: "..." }
  // In both cases data.youtube will be undefined — handle gracefully.
  const embedUrl = data?.youtube?.embed_url
  const searchQuery = data?.youtube?.query
  const locationLabel = typeof data?.location === 'string' ? data.location : null

  if (!data || !embedUrl) {
    return (
      <div className="card p-8 text-center text-slate-500">
        <Youtube className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p className="text-sm">
          {data?.detail || data?.error
            ? `YouTube unavailable: ${data.detail || data.error}`
            : 'No YouTube content available for this location.'}
        </p>
      </div>
    )
  }

  // ── Embed URL for the external "open on YouTube" link ─────────────────────
  // Convert embed URL → watch/search URL for the external link
  const externalUrl = searchQuery
    ? `https://www.youtube.com/results?search_query=${encodeURIComponent(searchQuery)}`
    : 'https://www.youtube.com'

  return (
    <div className="card overflow-hidden space-y-0">
      {/* Label row */}
      <div className="px-4 pt-4 pb-2 flex items-center justify-between gap-2 flex-wrap">
        {locationLabel && (
          <p className="text-xs text-slate-500 uppercase tracking-widest flex items-center gap-1">
            <Search className="w-3 h-3" />
            {searchQuery || locationLabel}
          </p>
        )}
        <a
          href={externalUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300 transition-colors ml-auto"
        >
          <ExternalLink className="w-3 h-3" />
          Open on YouTube
        </a>
      </div>

      {/* Iframe embed */}
      {iframeError ? (
        <div className="flex flex-col items-center justify-center gap-3 py-12 px-4 text-slate-500">
          <Youtube className="w-10 h-10 opacity-30" />
          <p className="text-sm text-center">
            Embed blocked by browser settings.{' '}
            <a
              href={externalUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sky-400 hover:underline"
            >
              Watch on YouTube instead
            </a>
          </p>
        </div>
      ) : (
        <div className="relative w-full" style={{ paddingBottom: '56.25%' /* 16:9 */ }}>
          <iframe
            className="absolute inset-0 w-full h-full"
            src={embedUrl}
            title={`YouTube: ${searchQuery || locationLabel || 'Location videos'}`}
            frameBorder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
            loading="lazy"
            onError={() => setIframeError(true)}
          />
        </div>
      )}
    </div>
  )
}

