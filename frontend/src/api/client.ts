/* ======================================================
   GeoMeasure Studio — API Client
   ====================================================== */

import axios from 'axios';
import type {
  UploadedFile,
  FileListItem,
  MeasurementsResponse,
  HealthResponse,
  ApiKeyMetadata,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  ApiKeyUsage,
  UsageSummary,
  KeyAnalytics,
  GeometryMeasurementRequest,
  PlaygroundExecutionResult,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  timeout: 60000, // 60s for large file uploads
});

/** Upload a .kml or .zip file */
export async function uploadFile(file: File): Promise<UploadedFile> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post<UploadedFile>('/api/files/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

/** List all uploaded files */
export async function listFiles(): Promise<FileListItem[]> {
  const { data } = await api.get<FileListItem[]>('/api/files/');
  return data;
}

/** Get file details (including GeoJSON) */
export async function getFile(fileId: string): Promise<UploadedFile> {
  const { data } = await api.get<UploadedFile>(`/api/files/${fileId}/`);
  return data;
}

/** Get measurements for a file */
export async function getMeasurements(fileId: string): Promise<MeasurementsResponse> {
  const { data } = await api.get<MeasurementsResponse>(
    `/api/files/${fileId}/measurements/`
  );
  return data;
}

/** Download measurements as CSV */
export function getCsvDownloadUrl(fileId: string): string {
  return `${API_URL}/api/files/${fileId}/measurements/?format=csv`;
}

/** Download measurements as GeoJSON */
export function getGeoJsonDownloadUrl(fileId: string): string {
  return `${API_URL}/api/files/${fileId}/measurements/?format=geojson`;
}

/** Health check */
export async function checkHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/api/health/');
  return data;
}

/** Delete an uploaded file */
export async function deleteFile(fileId: string): Promise<void> {
  await api.delete(`/api/files/${fileId}/`);
}

/* ======================================================
   v2 Phase 2: API Key Management API Endpoints
   ====================================================== */

/** List all API keys owned by the authenticated user */
export async function listApiKeys(accessToken: string): Promise<ApiKeyMetadata[]> {
  const { data } = await api.get<ApiKeyMetadata[]>('/api/keys/', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

/** Create a new API key (returns plaintext key once) */
export async function createApiKey(
  payload: CreateApiKeyRequest,
  accessToken: string
): Promise<CreateApiKeyResponse> {
  const { data } = await api.post<CreateApiKeyResponse>('/api/keys/', payload, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

/** Retrieve key metadata by ID */
export async function getApiKey(
  keyId: string,
  accessToken: string
): Promise<ApiKeyMetadata> {
  const { data } = await api.get<ApiKeyMetadata>(`/api/keys/${keyId}/`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

/** Revoke an API key immediately */
export async function revokeApiKey(
  keyId: string,
  accessToken: string
): Promise<ApiKeyMetadata> {
  const { data } = await api.delete<ApiKeyMetadata>(`/api/keys/${keyId}/`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

/** Retrieve key usage metrics */
export async function getApiKeyUsage(
  keyId: string,
  accessToken: string
): Promise<ApiKeyUsage> {
  const { data } = await api.get<ApiKeyUsage>(`/api/keys/${keyId}/usage/`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

/** Retrieve aggregate usage analytics across all owned keys */
export async function getUsageSummary(accessToken: string): Promise<UsageSummary> {
  const { data } = await api.get<UsageSummary>('/api/keys/usage/summary/', {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

/** Retrieve granular analytics for a single API key */
export async function getKeyAnalytics(
  keyId: string,
  accessToken: string
): Promise<KeyAnalytics> {
  const { data } = await api.get<KeyAnalytics>(`/api/keys/${keyId}/analytics/`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  return data;
}

/**
 * Execute external geometry measurement via the API Playground.
 * Sends the request with the X-API-Key header, tracks latency, and captures rate-limit headers.
 */
export async function testMeasurementPlayground(
  payload: GeometryMeasurementRequest,
  apiKey: string
): Promise<PlaygroundExecutionResult> {
  const startTime = performance.now();
  try {
    const res = await api.post('/api/v1/measurements/', payload, {
      headers: {
        'X-API-Key': apiKey.trim(),
        'Content-Type': 'application/json',
      },
    });
    const durationMs = Math.round(performance.now() - startTime);
    const headers = {
      rateLimitLimit: res.headers['x-ratelimit-limit'] ?? res.headers['X-RateLimit-Limit'],
      rateLimitRemaining: res.headers['x-ratelimit-remaining'] ?? res.headers['X-RateLimit-Remaining'],
      rateLimitReset: res.headers['x-ratelimit-reset'] ?? res.headers['X-RateLimit-Reset'],
      retryAfter: res.headers['retry-after'] ?? res.headers['Retry-After'],
    };
    return {
      status: res.status,
      statusText: res.statusText || 'OK',
      durationMs,
      data: res.data,
      headers,
    };
  } catch (err: unknown) {
    const durationMs = Math.round(performance.now() - startTime);
    if (axios.isAxiosError(err)) {
      const respHeaders = err.response?.headers;
      const headers = respHeaders ? {
        rateLimitLimit: respHeaders['x-ratelimit-limit'] ?? respHeaders['X-RateLimit-Limit'],
        rateLimitRemaining: respHeaders['x-ratelimit-remaining'] ?? respHeaders['X-RateLimit-Remaining'],
        rateLimitReset: respHeaders['x-ratelimit-reset'] ?? respHeaders['X-RateLimit-Reset'],
        retryAfter: respHeaders['retry-after'] ?? respHeaders['Retry-After'],
      } : undefined;
      return {
        status: err.response?.status || 500,
        statusText: err.response?.statusText || 'Error',
        durationMs,
        data: err.response?.data || { detail: err.message },
        headers,
        error: err.response?.data?.detail || err.message,
      };
    }
    return {
      status: 500,
      statusText: 'Internal Error',
      durationMs,
      data: { detail: err instanceof Error ? err.message : 'Unknown network failure' },
      error: err instanceof Error ? err.message : 'Unknown network failure',
    };
  }
}


