/* ======================================================
   GeoMeasure Studio — API Client
   ====================================================== */

import axios from 'axios';
import type {
  UploadedFile,
  FileListItem,
  MeasurementsResponse,
  HealthResponse,
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

