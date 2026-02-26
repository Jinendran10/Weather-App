import React, { useState } from 'react'
import { Trash2, Eye, Pencil, ChevronDown, ChevronUp, MapPin, Calendar, CheckCircle, XCircle, Clock } from 'lucide-react'
import { weatherApi } from '../services/api'
import toast from 'react-hot-toast'

const STATUS_BADGE = {
  success: { icon: CheckCircle, cls: 'text-green-400 bg-green-500/10 border-green-500/20' },
  failed: { icon: XCircle, cls: 'text-red-400 bg-red-500/10 border-red-500/20' },
  pending: { icon: Clock, cls: 'text-amber-400 bg-amber-500/10 border-amber-500/20' },
}

function StatusBadge({ status }) {
  const cfg = STATUS_BADGE[status] || STATUS_BADGE.pending
  const Icon = cfg.icon
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full border ${cfg.cls}`}>
      <Icon className="w-3 h-3" />
      {status}
    </span>
  )
}

function EditModal({ query, onSave, onClose }) {
  const [label, setLabel] = useState(query.label || '')
  const [notes, setNotes] = useState(query.notes || '')
  const [saving, setSaving] = useState(false)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave(query.id, { label, notes })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="card p-6 w-full max-w-md space-y-4">
        <h3 className="text-lg font-bold">Edit Query</h3>
        <div>
          <label className="label">Label</label>
          <input
            className="input"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            maxLength={300}
          />
        </div>
        <div>
          <label className="label">Notes</label>
          <textarea
            className="input resize-none"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={2000}
          />
        </div>
        <div className="flex gap-2 justify-end">
          <button className="btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  )
}

/**
 * WeatherHistory – renders a list of stored queries with expand, edit, delete.
 */
export default function WeatherHistory({ queries, onRefresh, onViewQuery }) {
  const [expandedId, setExpandedId] = useState(null)
  const [editQuery, setEditQuery] = useState(null)

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this query and all its weather records?')) return
    await toast.promise(weatherApi.deleteQuery(id), {
      loading: 'Deleting…',
      success: 'Query deleted.',
      error: 'Delete failed.',
    })
    onRefresh()
  }

  const handleSave = async (id, updates) => {
    await toast.promise(weatherApi.updateQuery(id, updates), {
      loading: 'Updating…',
      success: 'Query updated.',
      error: 'Update failed.',
    })
    onRefresh()
  }

  if (!queries || queries.length === 0) {
    return (
      <div className="text-center py-12 text-slate-500">
        <Calendar className="w-10 h-10 mx-auto mb-3 opacity-30" />
        <p className="text-lg">No weather queries yet.</p>
        <p className="text-sm mt-1">Use the form above to save your first query.</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {editQuery && (
        <EditModal query={editQuery} onSave={handleSave} onClose={() => setEditQuery(null)} />
      )}

      {queries.map((q) => {
        const isExpanded = expandedId === q.id
        return (
          <div key={q.id} className="card overflow-hidden">
            <div
              className="p-4 flex items-center gap-3 cursor-pointer hover:bg-slate-800/50 transition-colors"
              onClick={() => setExpandedId(isExpanded ? null : q.id)}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-semibold text-white truncate">
                    {q.label || q.location_name}
                  </p>
                  <StatusBadge status={q.status} />
                </div>
                <div className="flex items-center gap-3 mt-1 text-sm text-slate-400 flex-wrap">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3 h-3" /> {q.location_name}
                  </span>
                  <span className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {q.date_from} → {q.date_to}
                  </span>
                  <span className="text-slate-500 text-xs">{q.record_count} records</span>
                </div>
              </div>

              <div className="flex items-center gap-1.5 flex-shrink-0">
                <button
                  className="p-2 hover:bg-sky-500/20 rounded-lg text-sky-400 transition-colors"
                  title="View full details"
                  onClick={(e) => { e.stopPropagation(); onViewQuery(q.id) }}
                >
                  <Eye className="w-4 h-4" />
                </button>
                <button
                  className="p-2 hover:bg-slate-700 rounded-lg text-slate-400 transition-colors"
                  title="Edit label / notes"
                  onClick={(e) => { e.stopPropagation(); setEditQuery(q) }}
                >
                  <Pencil className="w-4 h-4" />
                </button>
                <button
                  className="p-2 hover:bg-red-500/20 rounded-lg text-red-400 transition-colors"
                  title="Delete query"
                  onClick={(e) => { e.stopPropagation(); handleDelete(q.id) }}
                >
                  <Trash2 className="w-4 h-4" />
                </button>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-slate-500" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-slate-500" />
                )}
              </div>
            </div>

            {/* Expanded: show mini record table */}
            {isExpanded && (
              <div className="border-t border-slate-700/50 px-4 pb-4 pt-3">
                <p className="text-xs text-slate-500 mb-3 uppercase tracking-widest">Quick preview</p>
                <div className="text-sm text-slate-300 space-y-1">
                  <p><span className="text-slate-500">Location:</span> {q.location_name}</p>
                  <p><span className="text-slate-500">Coordinates:</span> {q.latitude?.toFixed(4)}, {q.longitude?.toFixed(4)}</p>
                  <p><span className="text-slate-500">Date range:</span> {q.date_from} to {q.date_to}</p>
                  <p><span className="text-slate-500">Records:</span> {q.record_count}</p>
                  <p><span className="text-slate-500">Created:</span> {new Date(q.created_at).toLocaleString()}</p>
                </div>
                <button
                  className="btn-primary text-sm mt-4"
                  onClick={() => onViewQuery(q.id)}
                >
                  View Full Details & Charts
                </button>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
