/* ======================================================
   GeoMeasure Studio — Main Application
   ====================================================== */

import { useState, useEffect, useCallback } from 'react';
import FileUpload from './components/FileUpload';
import FileHistory from './components/FileHistory';
import MeasurementTable from './components/MeasurementTable';
import MapView from './components/MapView';
import ExportButtons from './components/ExportButtons';
import DiagnosticsPanel from './components/DiagnosticsPanel';
import { listFiles, getFile, getMeasurements, deleteFile } from './api/client';
import type { UploadedFile, FileListItem, Measurement } from './types';
import type { FeatureCollection } from 'geojson';

export default function App() {
  // State
  const [files, setFiles] = useState<FileListItem[]>([]);
  const [filesLoading, setFilesLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<UploadedFile | null>(null);
  const [measurements, setMeasurements] = useState<Measurement[]>([]);
  const [detailLoading, setDetailLoading] = useState(false);

  // Load file history on mount
  const loadFiles = useCallback(async () => {
    try {
      setFilesLoading(true);
      const data = await listFiles();
      setFiles(data);
    } catch (err) {
      console.error('Failed to load files:', err);
    } finally {
      setFilesLoading(false);
    }
  }, []);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  // Load file details when a file is selected
  const selectFile = useCallback(async (fileId: string) => {
    setSelectedId(fileId);
    setDetailLoading(true);
    try {
      const [file, measurementsData] = await Promise.all([
        getFile(fileId),
        getMeasurements(fileId),
      ]);
      setSelectedFile(file);
      setMeasurements(measurementsData.measurements);
    } catch (err) {
      console.error('Failed to load file details:', err);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  // Handle successful upload
  const handleUploadSuccess = useCallback(
    async (file: UploadedFile) => {
      await loadFiles();
      selectFile(file.id);
    },
    [loadFiles, selectFile]
  );

  // Handle file deletion
  const handleDeleteFile = useCallback(
    async (fileId: string) => {
      try {
        await deleteFile(fileId);
        if (selectedId === fileId) {
          setSelectedId(null);
          setSelectedFile(null);
          setMeasurements([]);
        }
        await loadFiles();
      } catch (err) {
        console.error('Failed to delete file:', err);
      }
    },
    [selectedId, loadFiles]
  );

  return (
    <div className="min-h-screen bg-surface-950">
      {/* Header */}
      <header className="border-b border-surface-800/60 bg-surface-950/80 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Logo */}
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-brand-500/20">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold gradient-text">GeoMeasure Studio</h1>
              <p className="text-xs text-surface-500 -mt-0.5">Geospatial File Measurement Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs text-surface-500">
            <span className="hidden sm:inline">v1.0.0</span>
            <a
              href="/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="btn-ghost text-xs"
            >
              API Docs ↗
            </a>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Sidebar — File Upload + History */}
          <div className="lg:col-span-4 space-y-5">
            <FileUpload onUploadSuccess={handleUploadSuccess} />
            <FileHistory
              files={files}
              selectedId={selectedId}
              onSelect={selectFile}
              onDelete={handleDeleteFile}
              loading={filesLoading}
            />
          </div>

          {/* Main panel — Map + Measurements */}
          <div className="lg:col-span-8 space-y-5">
            {/* Map */}
            <div className="glass-card p-4">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-surface-400 uppercase tracking-wider">
                  Map Preview
                </h2>
                {selectedFile && selectedFile.status === 'completed' && (
                  <ExportButtons
                    fileId={selectedFile.id}
                    filename={selectedFile.original_filename}
                  />
                )}
              </div>
              <MapView
                geojson={
                  selectedFile?.geojson
                    ? (selectedFile.geojson as unknown as FeatureCollection)
                    : null
                }
              />
            </div>

            {/* Measurements table */}
            {detailLoading ? (
              <div className="glass-card p-8">
                <div className="flex items-center justify-center gap-3">
                  <div className="w-5 h-5 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
                  <span className="text-surface-400">Loading measurements...</span>
                </div>
              </div>
            ) : selectedFile && measurements.length > 0 ? (
              <div className="glass-card p-4">
                <h2 className="text-sm font-semibold text-surface-400 uppercase tracking-wider mb-3">
                  Measurements
                </h2>
                <MeasurementTable
                  measurements={measurements}
                  sourceCrs={selectedFile.source_crs}
                />
              </div>
            ) : selectedFile ? (
              <div className="glass-card p-8 text-center text-surface-500">
                {selectedFile.status === 'error'
                  ? `Processing failed: ${selectedFile.error_message}`
                  : 'No measurements available for this file.'}
              </div>
            ) : null}

            {/* Diagnostics panel */}
            {selectedFile && <DiagnosticsPanel file={selectedFile} />}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-surface-800/40 mt-16 py-6">
        <div className="max-w-7xl mx-auto px-6 text-center text-xs text-surface-600">
          <p>GeoMeasure Studio — Built with FastAPI, GeoPandas, React & Leaflet</p>
        </div>
      </footer>
    </div>
  );
}
