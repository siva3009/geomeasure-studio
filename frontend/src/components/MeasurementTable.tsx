/* ======================================================
   MeasurementTable — Display measurement results
   ====================================================== */

import type { Measurement } from '../types';
import { formatArea, formatLength } from '../utils/format';

interface MeasurementTableProps {
  measurements: Measurement[];
  sourceCrs: string | null;
}

function getGeomBadge(type: string) {
  switch (type) {
    case 'Point':
    case 'MultiPoint':
      return <span className="geom-point">● {type}</span>;
    case 'LineString':
    case 'MultiLineString':
      return <span className="geom-line">━ {type}</span>;
    case 'Polygon':
    case 'MultiPolygon':
      return <span className="geom-polygon">⬡ {type}</span>;
    default:
      return <span className="badge bg-surface-700 text-surface-300">{type}</span>;
  }
}

export default function MeasurementTable({ measurements, sourceCrs }: MeasurementTableProps) {
  if (measurements.length === 0) {
    return (
      <div className="text-center py-8 text-surface-500">
        No measurement data available.
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      {/* CRS info bar */}
      <div className="flex items-center gap-4 mb-4 px-1 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="text-surface-500">Source CRS:</span>
          <span className="font-mono text-brand-300 bg-brand-500/10 px-2 py-0.5 rounded-md">
            {sourceCrs || 'Unknown'}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-surface-500">Features:</span>
          <span className="font-mono text-surface-300">{measurements.length}</span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-surface-700/50">
        <table className="w-full text-sm" id="measurement-table">
          <thead>
            <tr className="bg-surface-800/80 text-surface-400 text-xs uppercase tracking-wider">
              <th className="px-4 py-3 text-left font-medium">#</th>
              <th className="px-4 py-3 text-left font-medium">Feature ID</th>
              <th className="px-4 py-3 text-left font-medium">Geometry</th>
              <th className="px-4 py-3 text-left font-medium">Measurement CRS</th>
              <th className="px-4 py-3 text-right font-medium">Area</th>
              <th className="px-4 py-3 text-right font-medium">Length</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-800/50">
            {measurements.map((m, i) => (
              <tr
                key={i}
                className="hover:bg-surface-800/40 transition-colors duration-150"
              >
                <td className="px-4 py-3 text-surface-500 font-mono text-xs">
                  {m.feature_index}
                </td>
                <td className="px-4 py-3 text-surface-300 font-medium">
                  {m.feature_id || <span className="text-surface-600 italic">—</span>}
                </td>
                <td className="px-4 py-3">{getGeomBadge(m.geometry_type)}</td>
                <td className="px-4 py-3 font-mono text-xs text-surface-400">
                  {m.measurement_crs || <span className="text-surface-600">N/A</span>}
                </td>
                <td className="px-4 py-3 text-right font-mono text-emerald-400">
                  {formatArea(m.area_sq_meters)}
                </td>
                <td className="px-4 py-3 text-right font-mono text-cyan-400">
                  {formatLength(m.length_meters)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
