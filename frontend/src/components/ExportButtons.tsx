/* ======================================================
   ExportButtons — CSV and GeoJSON download buttons
   ====================================================== */

import { getCsvDownloadUrl, getGeoJsonDownloadUrl } from '../api/client';

interface ExportButtonsProps {
  fileId: string;
  filename: string;
}

export default function ExportButtons({ fileId, filename }: ExportButtonsProps) {
  const baseName = filename.replace(/\.[^/.]+$/, '');

  return (
    <div className="flex items-center gap-2">
      <a
        href={getCsvDownloadUrl(fileId)}
        download={`${baseName}_measurements.csv`}
        className="btn-secondary text-xs flex items-center gap-1.5"
        id="export-csv"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        CSV
      </a>
      <a
        href={getGeoJsonDownloadUrl(fileId)}
        download={`${baseName}_measurements.geojson`}
        className="btn-secondary text-xs flex items-center gap-1.5"
        id="export-geojson"
      >
        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" />
        </svg>
        GeoJSON
      </a>
    </div>
  );
}
