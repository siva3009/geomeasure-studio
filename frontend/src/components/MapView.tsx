/* ======================================================
   MapView — Leaflet map for GeoJSON visualization
   ====================================================== */

import { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import type { FeatureCollection } from 'geojson';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix default marker icon issue in Leaflet + bundlers
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

interface MapViewProps {
  geojson: FeatureCollection | null;
}

/** Auto-fit map bounds when GeoJSON changes */
function FitBounds({ geojson }: { geojson: FeatureCollection | null }) {
  const map = useMap();

  useEffect(() => {
    if (!geojson || !geojson.features || geojson.features.length === 0) return;
    try {
      const layer = L.geoJSON(geojson);
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
      }
    } catch {
      // ignore invalid geometries
    }
  }, [geojson, map]);

  return null;
}

/** Style features by geometry type */
function featureStyle(feature: GeoJSON.Feature | undefined) {
  const type = feature?.geometry?.type;
  switch (type) {
    case 'Polygon':
    case 'MultiPolygon':
      return {
        fillColor: '#10b981',
        fillOpacity: 0.25,
        color: '#34d399',
        weight: 2,
        opacity: 0.8,
      };
    case 'LineString':
    case 'MultiLineString':
      return {
        color: '#06b6d4',
        weight: 3,
        opacity: 0.8,
      };
    default:
      return {
        fillColor: '#6366f1',
        color: '#818cf8',
        weight: 2,
        fillOpacity: 0.3,
      };
  }
}

/** Create popup content for each feature */
function onEachFeature(feature: GeoJSON.Feature, layer: L.Layer) {
  const props = feature.properties || {};
  const lines: string[] = [];

  // Show measurement data first
  if (props._area_sq_meters != null) {
    const val = props._area_sq_meters >= 1_000_000
      ? `${(props._area_sq_meters / 1_000_000).toFixed(4)} km²`
      : `${props._area_sq_meters.toFixed(2)} m²`;
    lines.push(`<b>Area:</b> ${val}`);
  }
  if (props._length_meters != null) {
    const val = props._length_meters >= 1000
      ? `${(props._length_meters / 1000).toFixed(4)} km`
      : `${props._length_meters.toFixed(2)} m`;
    lines.push(`<b>Length:</b> ${val}`);
  }
  if (props._measurement_crs) {
    lines.push(`<b>CRS:</b> <code>${props._measurement_crs}</code>`);
  }

  // Show other properties
  for (const [key, val] of Object.entries(props)) {
    if (!key.startsWith('_') && val != null && val !== '') {
      lines.push(`<b>${key}:</b> ${String(val)}`);
    }
  }

  if (lines.length > 0) {
    layer.bindPopup(
      `<div style="font-size: 13px; line-height: 1.6; max-width: 250px">${lines.join('<br/>')}</div>`
    );
  }
}

export default function MapView({ geojson }: MapViewProps) {
  const geoJsonRef = useRef<L.GeoJSON | null>(null);

  if (!geojson || !geojson.features || geojson.features.length === 0) {
    return (
      <div className="h-[400px] rounded-2xl bg-surface-900/60 border border-surface-700/50 flex items-center justify-center" id="map-placeholder">
        <div className="text-center">
          <svg className="w-12 h-12 mx-auto text-surface-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          <p className="text-surface-500 text-sm">Upload a file to view on the map</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-[400px] rounded-2xl overflow-hidden border border-surface-700/50 animate-fade-in" id="map-container">
      <MapContainer
        center={[20, 78]}
        zoom={5}
        className="h-full w-full"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        <GeoJSON
          key={JSON.stringify(geojson).slice(0, 100)}
          data={geojson}
          style={featureStyle}
          onEachFeature={onEachFeature}
          ref={geoJsonRef}
        />
        <FitBounds geojson={geojson} />
      </MapContainer>
    </div>
  );
}
