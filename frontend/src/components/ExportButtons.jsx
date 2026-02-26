import React from 'react'
import { Download, FileJson, FileSpreadsheet } from 'lucide-react'
import { exportApi } from '../services/api'
import toast from 'react-hot-toast'

/**
 * ExportButtons – triggers CSV or JSON export with optional query_id filtering.
 */
export default function ExportButtons({ queryIds = null, label = 'Export Data' }) {
  const handleExport = async (format) => {
    const payload = {
      format,
      include_records: true,
    }
    if (queryIds && queryIds.length > 0) {
      payload.query_ids = queryIds
    }

    const promise = exportApi.exportData(payload)
    toast.promise(promise, {
      loading: `Preparing ${format.toUpperCase()} export…`,
      success: `${format.toUpperCase()} downloaded!`,
      error: 'Export failed.',
    })
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-slate-400 mr-1">{label}:</span>
      <button
        onClick={() => handleExport('csv')}
        className="btn-secondary text-sm flex items-center gap-1.5 !px-3 !py-2"
        title="Export as CSV"
      >
        <FileSpreadsheet className="w-4 h-4 text-green-400" />
        CSV
      </button>
      <button
        onClick={() => handleExport('json')}
        className="btn-secondary text-sm flex items-center gap-1.5 !px-3 !py-2"
        title="Export as JSON"
      >
        <FileJson className="w-4 h-4 text-amber-400" />
        JSON
      </button>
    </div>
  )
}
