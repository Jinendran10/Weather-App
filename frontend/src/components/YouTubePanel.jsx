import React from 'react'
import { Youtube, ExternalLink } from 'lucide-react'

/**
 * YouTubePanel – displays a grid of YouTube video cards for a location.
 */
export default function YouTubePanel({ data, loading = false }) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="card p-0 overflow-hidden animate-pulse">
            <div className="bg-slate-700 aspect-video" />
            <div className="p-3 space-y-2">
              <div className="h-4 bg-slate-700 rounded w-3/4" />
              <div className="h-3 bg-slate-700 rounded w-1/2" />
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!data || data.videos.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        <Youtube className="w-8 h-8 mx-auto mb-2 opacity-40" />
        <p>No videos found for this location.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-slate-500 uppercase tracking-widest">
        YouTube results for "{data.location}"
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.videos.map((v) => (
          <a
            key={v.video_id}
            href={v.youtube_url}
            target="_blank"
            rel="noopener noreferrer"
            className="card overflow-hidden hover:border-sky-500/50 transition-colors group"
          >
            <div className="relative aspect-video overflow-hidden bg-slate-800">
              <img
                src={v.thumbnail_url}
                alt={v.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                loading="lazy"
              />
              <div className="absolute inset-0 flex items-center justify-center bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity">
                <Youtube className="w-12 h-12 text-red-500" />
              </div>
            </div>
            <div className="p-3 space-y-1">
              <p className="text-sm font-semibold text-slate-100 line-clamp-2 leading-snug">
                {v.title}
              </p>
              <p className="text-xs text-slate-500">{v.channel_title}</p>
              <div className="flex items-center gap-1 text-xs text-sky-400 mt-1">
                <ExternalLink className="w-3 h-3" />
                Watch on YouTube
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  )
}
