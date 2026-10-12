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
  highlightedIndices?: number[];
}

/** Check if geometry has valid displayable coordinates */
function hasValidCoordinates(geometry: GeoJSON.Geometry | null | undefined): boolean {
  if (!geometry) return false;
  if (geometry.type === 'GeometryCollection') {
    return Array.isArray(geometry.geometries) && geometry.geometries.some(hasValidCoordinates);
  }
  if (!('coordinates' in geometry) || !Array.isArray(geometry.coordinates)) {
    return false;
  }
  if (geometry.coordinates.length === 0) {
    return false;
  }
  if (geometry.type === 'Point') {
    const [lon, lat] = geometry.coordinates;
    return (
      typeof lon === 'number' &&
      typeof lat === 'number' &&
      !isNaN(lon) &&
      !isNaN(lat) &&
      isFinite(lon) &&
      isFinite(lat)
    );
  }
  return true;
}

/** Check if dataset contains at least one usable geometry */
function hasUsableGeometry(geojson: FeatureCollection | null): boolean {
  if (!geojson || !geojson.features || !Array.isArray(geojson.features) || geojson.features.length === 0) {
    return false;
  }
  return geojson.features.some((f) => f && hasValidCoordinates(f.geometry));
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

/** Style features by geometry type and highlight state */
function featureStyle(feature: GeoJSON.Feature | undefined, highlightedIndices: number[] = []) {
  const featIndex = feature?.properties?._feature_index;
  const isHighlighted = typeof featIndex === 'number' && highlightedIndices.includes(featIndex);

  if (isHighlighted) {
    return {
      fillColor: '#f59e0b',
      fillOpacity: 0.55,
      color: '#fbbf24',
      weight: 3.5,
      opacity: 1,
      dashArray: '4, 4',
    };
  }

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
    case 'Point':
    case 'MultiPoint':
      return {
        fillColor: '#6366f1',
        color: '#a5b4fc',
        weight: 2,
        opacity: 0.9,
        fillOpacity: 0.75,
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

/** Render Point / MultiPoint features with consistent styling */
function pointToLayer(feature: GeoJSON.Feature, latlng: L.LatLng, highlightedIndices: number[] = []): L.Layer {
  const featIndex = feature?.properties?._feature_index;
  const isHighlighted = typeof featIndex === 'number' && highlightedIndices.includes(featIndex);

  return L.circleMarker(latlng, {
    radius: isHighlighted ? 10 : 7,
    fillColor: isHighlighted ? '#f59e0b' : '#6366f1',
    color: isHighlighted ? '#fbbf24' : '#a5b4fc',
    weight: isHighlighted ? 3 : 2,
    opacity: 1,
    fillOpacity: isHighlighted ? 0.9 : 0.75,
  });
}

/** Create popup and hover tooltip content for each feature */
function onEachFeature(feature: GeoJSON.Feature, layer: L.Layer) {
  const props = feature.properties || {};
  const lines: string[] = [];

  // Determine label for hover tooltip
  const name =
    props.name ||
    props.Name ||
    props.NAME ||
    props.parcel ||
    props.parcel_name ||
    props.id ||
    props.ID ||
    feature.id;

  const tooltipLabel = name
    ? `${String(name)} (${feature.geometry?.type || 'Feature'})`
    : `${feature.geometry?.type || 'Feature'}`;

  layer.bindTooltip(tooltipLabel, {
    sticky: true,
    direction: 'top',
    offset: [0, -4],
  });

  // Show measurement data first
  if (props._area_sq_meters != null) {
    const val =
      props._area_sq_meters >= 1_000_000
        ? `${(props._area_sq_meters / 1_000_000).toFixed(4)} km²`
        : `${props._area_sq_meters.toFixed(2)} m²`;
    lines.push(`<b>Area:</b> ${val}`);
  }
  if (props._length_meters != null) {
    const val =
      props._length_meters >= 1000
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

export default function MapView({ geojson, highlightedIndices = [] }: MapViewProps) {
  const geoJsonRef = useRef<L.GeoJSON | null>(null);

  // Initial state: no file uploaded yet
  if (!geojson) {
    return (
      <div
        className="h-[400px] rounded-2xl bg-surface-900/60 border border-surface-700/50 flex items-center justify-center"
        id="map-placeholder"
      >
        <div className="text-center p-6">
          <svg
            className="w-12 h-12 mx-auto text-surface-600 mb-2"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1}
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
            />
          </svg>
          <p className="text-surface-500 text-sm">Upload a file to view on the map</p>
        </div>
      </div>
    );
  }

  // Dataset uploaded, but has no usable geometry
  if (!hasUsableGeometry(geojson)) {
    return (
      <div
        className="h-[400px] rounded-2xl bg-surface-900/60 border border-surface-700/50 flex items-center justify-center"
        id="map-no-geometry"
      >
        <div className="text-center p-6 max-w-sm">
          <div className="w-12 h-12 mx-auto rounded-full bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 mb-3">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
          </div>
          <h3 className="text-surface-200 font-medium text-sm mb-1">No Usable Geometry</h3>
          <p className="text-surface-400 text-xs leading-relaxed">
            This dataset contains no displayable geometric features or valid geographic coordinates to render on the map.
          </p>
        </div>
      </div>
    );
  }

  const annotatedGeojson: FeatureCollection = {
    ...geojson,
    features: geojson.features.map((f, idx) => ({
      ...f,
      properties: { ...(f.properties || {}), _feature_index: idx },
    })),
  };

  return (
    <div
      className="h-[400px] rounded-2xl overflow-hidden border border-surface-700/50 animate-fade-in"
      id="map-container"
    >
      <MapContainer
        center={[20, 78]}
        zoom={5}
        className="h-full w-full"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <GeoJSON
          key={`${JSON.stringify(geojson).slice(0, 80)}_${highlightedIndices.join(',')}`}
          data={annotatedGeojson}
          style={(feature) => featureStyle(feature, highlightedIndices)}
          pointToLayer={(feature, latlng) => pointToLayer(feature, latlng, highlightedIndices)}
          onEachFeature={onEachFeature}
          ref={geoJsonRef}
        />
        <FitBounds geojson={geojson} />
      </MapContainer>
    </div>
  );
}
