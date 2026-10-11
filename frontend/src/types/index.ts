/* ======================================================
   GeoMeasure Studio — TypeScript Type Definitions
   ====================================================== */

export interface UploadedFile {
  id: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  source_crs: string | null;
  feature_count: number | null;
  status: 'processing' | 'completed' | 'error';
  error_message: string | null;
  geojson: GeoJSON.FeatureCollection | null;
  created_at: string;
}

export interface FileListItem {
  id: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  feature_count: number | null;
  status: string;
  created_at: string;
}

export interface Measurement {
  feature_index: number;
  feature_id: string | null;
  geometry_type: string;
  source_crs: string | null;
  measurement_crs: string | null;
  area_sq_meters: number | null;
  length_meters: number | null;
  measurement_unit: string;
  properties: Record<string, unknown> | null;
}

export interface MeasurementsResponse {
  file_id: string;
  measurements: Measurement[];
}

export interface HealthResponse {
  status: string;
  database: string;
  timestamp: string;
}
