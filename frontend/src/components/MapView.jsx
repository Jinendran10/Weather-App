import React, { useEffect, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'

// Fix default Leaflet marker icons
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

function RecenterMap({ lat, lon }) {
  const map = useMap()
  useEffect(() => {
    if (lat && lon) map.setView([lat, lon], 12)
  }, [lat, lon, map])
  return null
}

/**
 * MapView – renders a Leaflet map with a marker at the given coordinates.
 * Falls back to OpenStreetMap tiles (no API key required).
 */
export default function MapView({ latitude, longitude, locationName, height = '300px' }) {
  if (!latitude || !longitude) return null

  return (
    <div className="rounded-xl overflow-hidden border border-slate-700/50" style={{ height }}>
      <MapContainer
        center={[latitude, longitude]}
        zoom={12}
        scrollWheelZoom={false}
        style={{ height: '100%', width: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <Marker position={[latitude, longitude]}>
          <Popup>
            <strong>{locationName || `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`}</strong>
          </Popup>
        </Marker>
        <RecenterMap lat={latitude} lon={longitude} />
      </MapContainer>
    </div>
  )
}
