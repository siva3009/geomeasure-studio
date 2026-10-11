/* ======================================================
   FileHistory — File list with selection support
   ====================================================== */

import type { FileListItem } from '../types';
import { formatFileSize, formatDate } from '../utils/format';

interface FileHistoryProps {
  files: FileListItem[];
  selectedId: string | null;
  onSelect: (fileId: string) => void;
  onDelete?: (fileId: string) => void;
  loading: boolean;
}

function getStatusBadge(status: string) {
  switch (status) {
    case 'completed':
      return <span className="badge-completed">✓ Completed</span>;
    case 'processing':
      return <span className="badge-processing">⟳ Processing</span>;
    case 'error':
      return <span className="badge-error">✗ Error</span>;
    default:
      return <span className="badge">{status}</span>;
  }
}

function getFileIcon(type: string) {
  if (type === 'kml') {
    return (
      <div className="w-9 h-9 rounded-lg bg-amber-500/15 flex items-center justify-center border border-amber-500/20 flex-shrink-0">
        <span className="text-amber-400 text-xs font-mono font-bold">KML</span>
      </div>
    );
  }
  return (
    <div className="w-9 h-9 rounded-lg bg-violet-500/15 flex items-center justify-center border border-violet-500/20 flex-shrink-0">
      <span className="text-violet-400 text-xs font-mono font-bold">SHP</span>
    </div>
  );
}

export default function FileHistory({ files, selectedId, onSelect, onDelete, loading }: FileHistoryProps) {
  if (loading) {
    return (
      <div className="glass-card p-6">
        <h2 className="text-sm font-semibold text-surface-400 uppercase tracking-wider mb-4">File History</h2>
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 rounded-xl bg-surface-800/50 animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="glass-card p-6">
        <h2 className="text-sm font-semibold text-surface-400 uppercase tracking-wider mb-4">File History</h2>
        <p className="text-surface-500 text-sm text-center py-8">
          No files uploaded yet. Upload a .kml or .zip file to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="glass-card p-4">
      <h2 className="text-sm font-semibold text-surface-400 uppercase tracking-wider mb-3 px-2">
        File History
        <span className="ml-2 text-xs font-normal text-surface-500">({files.length})</span>
      </h2>
      <div className="space-y-1 max-h-[400px] overflow-y-auto pr-1">
        {files.map((file) => (
          <div
            key={file.id}
            id={`file-${file.id}`}
            onClick={() => onSelect(file.id)}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') onSelect(file.id);
            }}
            className={`
              w-full text-left px-3 py-3 rounded-xl transition-all duration-200
              flex items-center gap-3 group cursor-pointer
              ${selectedId === file.id
                ? 'bg-brand-500/10 border border-brand-500/30 shadow-lg shadow-brand-500/5'
                : 'hover:bg-surface-800/80 border border-transparent'
              }
            `}
          >
            {getFileIcon(file.file_type)}
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-0.5">
                <span className="text-sm font-medium text-surface-200 truncate">
                  {file.original_filename}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs text-surface-500">
                <span>{formatFileSize(file.file_size_bytes)}</span>
                <span>·</span>
                <span>{file.feature_count ?? '—'} features</span>
                <span>·</span>
                {getStatusBadge(file.status)}
              </div>
              <div className="text-xs text-surface-600 mt-0.5">
                {formatDate(file.created_at)}
              </div>
            </div>
            {onDelete && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(file.id);
                }}
                className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-surface-500 hover:text-red-400 hover:bg-red-500/10 transition-all flex-shrink-0"
                title="Delete file"
                aria-label={`Delete ${file.original_filename}`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
