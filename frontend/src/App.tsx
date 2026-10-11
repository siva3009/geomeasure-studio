/* ======================================================
   GeoMeasure Studio — Main Application
   Workspace (v1) & Developer Portal (v2)
   ====================================================== */

import { useState, useEffect, useCallback } from 'react';
import FileUpload from './components/FileUpload';
import FileHistory from './components/FileHistory';
import MeasurementTable from './components/MeasurementTable';
import MapView from './components/MapView';
import ExportButtons from './components/ExportButtons';
import DiagnosticsPanel from './components/DiagnosticsPanel';
import { DeveloperPortal } from './components/developer/DeveloperPortal';
import { AuthProvider } from './context/AuthContext';
import { listFiles, getFile, getMeasurements, deleteFile } from './api/client';
import type { UploadedFile, FileListItem, Measurement } from './types';
import type { FeatureCollection } from 'geojson';

function MainLayout() {
  // Top-level navigation state ('workspace' | 'developer')
  const [currentView, setCurrentView] = useState<'workspace' | 'developer'>(() => {
    if (typeof window !== 'undefined' && window.location.pathname.startsWith('/developer')) {
      return 'developer';
    }
    return 'workspace';
  });

  // Sync with browser URL history
  useEffect(() => {
    const handlePopState = () => {
      if (window.location.pathname.startsWith('/developer')) {
        setCurrentView('developer');
      } else {
        setCurrentView('workspace');
      }
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  const navigateTo = (view: 'workspace' | 'developer') => {
    setCurrentView(view);
    const targetPath = view === 'developer' ? '/developer' : '/';
    if (window.location.pathname !== targetPath) {
      window.history.pushState(null, '', targetPath);
    }
  };

  // Workspace State
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
    <div className="min-h-screen bg-surface-950 flex flex-col justify-between">
      <div>
        {/* Header */}
        <header className="border-b border-surface-800/60 bg-surface-950/80 backdrop-blur-xl sticky top-0 z-50">
          <div className="max-w-7xl mx-auto px-6 py-3.5 flex flex-wrap items-center justify-between gap-4">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigateTo('workspace')}
                className="flex items-center gap-3 text-left focus:outline-none group"
              >
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-brand-500/20 group-hover:scale-105 transition-transform">
                  <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-base font-bold gradient-text">GeoMeasure Studio</h1>
                  <p className="text-[11px] text-surface-500 -mt-0.5">Geospatial Measurement Platform</p>
                </div>
              </button>
            </div>

            {/* View Switcher: Workspace vs Developer Portal */}
            <div className="flex items-center p-1 bg-surface-900/90 rounded-xl border border-surface-800">
              <button
                onClick={() => navigateTo('workspace')}
                className={`py-1.5 px-3.5 rounded-lg text-xs font-medium transition-all ${
                  currentView === 'workspace'
                    ? 'bg-brand-600 text-white shadow-sm font-semibold'
                    : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                Workspace
              </button>
              <button
                onClick={() => navigateTo('developer')}
                className={`py-1.5 px-3.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 ${
                  currentView === 'developer'
                    ? 'bg-gradient-to-r from-violet-600 to-indigo-600 text-white shadow-sm font-semibold'
                    : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-pulse" />
                Developer Portal
              </button>
            </div>

            {/* Quick Links */}
            <div className="flex items-center gap-3 text-xs text-surface-500">
              <span className="hidden sm:inline font-mono text-[11px] px-2 py-0.5 rounded bg-surface-900 border border-surface-800 text-surface-400">
                v2.0.0
              </span>
              <a
                href="https://geomeasure-backend.onrender.com/docs"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-ghost text-xs py-1 px-2.5 flex items-center gap-1"
              >
                <span>Swagger UI</span>
                <span className="text-[10px]">↗</span>
              </a>
            </div>
          </div>
        </header>

        {/* Main Content Area */}
        <main className="max-w-7xl mx-auto px-6 py-8">
          {currentView === 'developer' ? (
            <DeveloperPortal />
          ) : (
            /* Workspace View (Preserves all existing v1 features) */
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
          )}
        </main>
      </div>

      {/* Footer */}
      <footer className="border-t border-surface-800/40 mt-16 py-6 bg-surface-950/60">
        <div className="max-w-7xl mx-auto px-6 text-center text-xs text-surface-600 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p>GeoMeasure Studio v2 — Built with FastAPI, GeoPandas, React & Supabase</p>
          <div className="flex items-center gap-4 text-[11px] text-surface-500">
            <button
              onClick={() => navigateTo('workspace')}
              className="hover:text-surface-300 transition"
            >
              Workspace
            </button>
            <span>•</span>
            <button
              onClick={() => navigateTo('developer')}
              className="hover:text-surface-300 transition"
            >
              Developer Portal
            </button>
            <span>•</span>
            <a
              href="https://geomeasure-backend.onrender.com/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-surface-300 transition"
            >
              API Reference
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <MainLayout />
    </AuthProvider>
  );
}
