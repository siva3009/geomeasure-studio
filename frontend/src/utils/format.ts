/* ======================================================
   GeoMeasure Studio — Formatting Utilities
   ====================================================== */

/** Format bytes into human-readable size */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/** Format area with appropriate units */
export function formatArea(sqMeters: number | null): string {
  if (sqMeters === null || sqMeters === undefined) return '—';
  if (sqMeters >= 1_000_000) {
    return `${(sqMeters / 1_000_000).toFixed(4)} km²`;
  }
  if (sqMeters >= 10_000) {
    return `${(sqMeters / 10_000).toFixed(4)} ha`;
  }
  return `${sqMeters.toFixed(2)} m²`;
}

/** Format length with appropriate units */
export function formatLength(meters: number | null): string {
  if (meters === null || meters === undefined) return '—';
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(4)} km`;
  }
  return `${meters.toFixed(2)} m`;
}

/** Format ISO date string to local readable format */
export function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleString();
}

/** Get a color for geometry type badges */
export function getGeometryColor(type: string): string {
  switch (type) {
    case 'Point':
    case 'MultiPoint':
      return '#6366f1'; // indigo
    case 'LineString':
    case 'MultiLineString':
      return '#06b6d4'; // cyan
    case 'Polygon':
    case 'MultiPolygon':
      return '#10b981'; // emerald
    default:
      return '#6b7280'; // gray
  }
}
