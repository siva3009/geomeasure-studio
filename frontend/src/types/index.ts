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

/* ======================================================
   v2 Phase 2: API Key Management & Playground Types
   ====================================================== */

export interface ApiKeyMetadata {
  id: string;
  user_id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  request_count: number;
}

export interface CreateApiKeyRequest {
  name: string;
  expires_in_days?: number | null;
}

export interface CreateApiKeyResponse {
  id: string;
  name: string;
  prefix: string;
  api_key: string;
  created_at: string;
  expires_at: string | null;
}

export interface ApiKeyUsage {
  id: string;
  name: string;
  prefix: string;
  request_count: number;
  last_used_at: string | null;
  is_active: boolean;
}

export interface GeometryMeasurementRequest {
  geometry: Record<string, unknown>;
  crs?: string;
  properties?: Record<string, unknown>;
}

export interface GeometryMeasurementResponse {
  geometry_type: string;
  source_crs: string;
  measurement_crs: string | null;
  area_sq_meters: number | null;
  length_meters: number | null;
  area_hectares: number | null;
  area_sq_km: number | null;
  length_km: number | null;
  measurement_unit: string;
  properties: Record<string, unknown>;
}

export interface PlaygroundExecutionResult {
  status: number;
  statusText: string;
  durationMs: number;
  data: GeometryMeasurementResponse | Record<string, unknown>;
  error?: string;
}

