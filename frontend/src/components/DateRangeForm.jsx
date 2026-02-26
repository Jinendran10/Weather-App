import React, { useState } from 'react'
import DatePicker from 'react-datepicker'
import { Calendar, Tag, FileText, Loader2 } from 'lucide-react'
import { format, addDays } from 'date-fns'

/**
 * DateRangeForm – collects location, date_from, date_to, optional label/notes.
 * Validates date range client-side before submission.
 */
export default function DateRangeForm({ onSubmit, loading = false, initialLocation = '' }) {
  const [location, setLocation] = useState(initialLocation)
  const [dateFrom, setDateFrom] = useState(new Date())
  const [dateTo, setDateTo] = useState(new Date())
  const [label, setLabel] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')

    if (!location.trim()) {
      setError('Please enter a location.')
      return
    }
    if (dateFrom > dateTo) {
      setError('Start date must be on or before end date.')
      return
    }
    const days = Math.ceil((dateTo - dateFrom) / (1000 * 60 * 60 * 24))
    if (days > 365) {
      setError('Date range cannot exceed 365 days.')
      return
    }

    onSubmit({
      location: location.trim(),
      date_from: format(dateFrom, 'yyyy-MM-dd'),
      date_to: format(dateTo, 'yyyy-MM-dd'),
      label: label.trim() || undefined,
      notes: notes.trim() || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Location */}
      <div>
        <label className="label">Location</label>
        <input
          type="text"
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          placeholder="City, ZIP, GPS coordinates, or landmark…"
          className="input"
          disabled={loading}
          required
        />
      </div>

      {/* Date range */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="label flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" /> Start Date
          </label>
          <DatePicker
            selected={dateFrom}
            onChange={(d) => setDateFrom(d)}
            selectsStart
            startDate={dateFrom}
            endDate={dateTo}
            dateFormat="yyyy-MM-dd"
            className="input"
            disabled={loading}
            wrapperClassName="w-full"
          />
        </div>
        <div>
          <label className="label flex items-center gap-1.5">
            <Calendar className="w-3.5 h-3.5" /> End Date
          </label>
          <DatePicker
            selected={dateTo}
            onChange={(d) => setDateTo(d)}
            selectsEnd
            startDate={dateFrom}
            endDate={dateTo}
            minDate={dateFrom}
            dateFormat="yyyy-MM-dd"
            className="input"
            disabled={loading}
            wrapperClassName="w-full"
          />
        </div>
      </div>

      {/* Optional fields */}
      <div>
        <label className="label flex items-center gap-1.5">
          <Tag className="w-3.5 h-3.5" /> Label (optional)
        </label>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="e.g. Summer trip to Paris"
          className="input"
          disabled={loading}
          maxLength={300}
        />
      </div>

      <div>
        <label className="label flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5" /> Notes (optional)
        </label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          placeholder="Any additional context…"
          className="input resize-none"
          rows={3}
          disabled={loading}
          maxLength={2000}
        />
      </div>

      {/* Error */}
      {error && (
        <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2">
          {error}
        </p>
      )}

      <button type="submit" className="btn-primary w-full flex items-center justify-center gap-2" disabled={loading}>
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Fetching Weather Data…
          </>
        ) : (
          'Fetch & Save Weather Data'
        )}
      </button>
    </form>
  )
}
