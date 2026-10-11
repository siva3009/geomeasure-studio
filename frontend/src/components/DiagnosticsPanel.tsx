/* ======================================================
   DiagnosticsPanel — Processing diagnostics & file info
   ====================================================== */

import type { UploadedFile } from '../types';
import { formatFileSize, formatDate } from '../utils/format';

interface DiagnosticsPanelProps {
  file: UploadedFile;
}

export default function DiagnosticsPanel({ file }: DiagnosticsPanelProps) {
  return (
    <div className="glass-card p-4 animate-fade-in" id="diagnostics-panel">
      <h3 className="text-xs font-semibold text-surface-400 uppercase tracking-wider mb-3">
        Processing Info
      </h3>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <InfoItem label="Filename" value={file.original_filename} />
        <InfoItem label="File Type" value={file.file_type.toUpperCase()} />
        <InfoItem label="File Size" value={formatFileSize(file.file_size_bytes)} />
        <InfoItem label="Features" value={String(file.feature_count ?? '—')} />
        <InfoItem label="Source CRS" value={file.source_crs || 'Unknown'} mono />
        <InfoItem label="Status" value={file.status} />
        <InfoItem label="Uploaded" value={formatDate(file.created_at)} />
        {file.error_message && (
          <div className="col-span-2">
            <InfoItem label="Error" value={file.error_message} error />
          </div>
        )}
      </div>
    </div>
  );
}

function InfoItem({
  label,
  value,
  mono,
  error,
}: {
  label: string;
  value: string;
  mono?: boolean;
  error?: boolean;
}) {
  return (
    <div>
      <dt className="text-xs text-surface-500 mb-0.5">{label}</dt>
      <dd
        className={`text-sm ${
          error
            ? 'text-red-400'
            : mono
            ? 'font-mono text-brand-300'
            : 'text-surface-200'
        }`}
      >
        {value}
      </dd>
    </div>
  );
}
