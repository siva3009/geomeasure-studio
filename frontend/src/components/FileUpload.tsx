/* ======================================================
   FileUpload — Drag-and-drop file upload component
   ====================================================== */

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { uploadFile } from '../api/client';
import type { UploadedFile } from '../types';

interface FileUploadProps {
  onUploadSuccess: (file: UploadedFile) => void;
}

export default function FileUpload({ onUploadSuccess }: FileUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<string>('');

  const onDrop = useCallback(
    async (acceptedFiles: File[]) => {
      if (acceptedFiles.length === 0) return;

      const file = acceptedFiles[0];
      setUploading(true);
      setError(null);
      setProgress(`Processing ${file.name}...`);

      try {
        const result = await uploadFile(file);
        onUploadSuccess(result);
        setProgress('');
      } catch (err: unknown) {
        if (err && typeof err === 'object' && 'response' in err) {
          const axiosErr = err as { response?: { data?: { detail?: string } } };
          setError(axiosErr.response?.data?.detail || 'Upload failed');
        } else {
          setError('Upload failed — check your connection.');
        }
        setProgress('');
      } finally {
        setUploading(false);
      }
    },
    [onUploadSuccess]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/vnd.google-earth.kml+xml': ['.kml'],
      'application/zip': ['.zip'],
    },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="animate-fade-in">
      <div
        {...getRootProps()}
        id="file-upload-dropzone"
        className={`
          relative overflow-hidden rounded-2xl border-2 border-dashed
          transition-all duration-300 cursor-pointer group
          ${isDragActive
            ? 'border-brand-400 bg-brand-500/10 scale-[1.01]'
            : 'border-surface-600/50 hover:border-brand-500/50 hover:bg-surface-800/50'
          }
          ${uploading ? 'opacity-60 pointer-events-none' : ''}
        `}
      >
        {/* Background gradient glow */}
        <div className="absolute inset-0 bg-gradient-to-br from-brand-600/5 via-transparent to-cyan-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

        <div className="relative px-8 py-12 text-center">
          <input {...getInputProps()} />

          {/* Icon */}
          <div className="mx-auto w-16 h-16 mb-4 rounded-2xl bg-gradient-to-br from-brand-500/20 to-cyan-500/20 flex items-center justify-center border border-brand-500/20 group-hover:scale-110 transition-transform duration-300">
            <svg className="w-8 h-8 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>

          {uploading ? (
            <>
              <div className="flex items-center justify-center gap-2 mb-2">
                <div className="w-4 h-4 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
                <span className="text-brand-300 font-medium">Processing...</span>
              </div>
              <p className="text-sm text-surface-400">{progress}</p>
            </>
          ) : isDragActive ? (
            <p className="text-lg font-medium text-brand-300">Drop your file here</p>
          ) : (
            <>
              <p className="text-lg font-medium text-surface-200 mb-1">
                Drag & drop a geospatial file
              </p>
              <p className="text-sm text-surface-400">
                or <span className="text-brand-400 underline underline-offset-2">browse</span> to select
              </p>
              <p className="text-xs text-surface-500 mt-3">
                Supports <span className="text-surface-300 font-mono">.kml</span> and
                <span className="text-surface-300 font-mono"> .zip</span> (Shapefile) — max 50 MB
              </p>
            </>
          )}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mt-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-sm animate-slide-up" id="upload-error">
          <span className="font-medium">Error:</span> {error}
        </div>
      )}
    </div>
  );
}
