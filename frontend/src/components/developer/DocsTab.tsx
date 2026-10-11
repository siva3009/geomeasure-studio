/* ======================================================
   GeoMeasure Studio — API Documentation Tab
   Reference, Schemas, Geospatial CRS Policies & Error Guide
   ====================================================== */

import React from 'react';

export const DocsTab: React.FC = () => {
  return (
    <div className="space-y-8 max-w-5xl">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-white">Developer API Reference</h2>
        <p className="text-xs text-surface-400 mt-1">
          Complete programmatic documentation for GeoMeasure Studio v2 external geometry measurement and key management endpoints.
        </p>
      </div>

      {/* Quick Links & Base URL */}
      <div className="glass-card p-5 border border-surface-700/40 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <span className="text-[11px] text-surface-500 uppercase tracking-wider font-semibold block">Production Base URL</span>
          <span className="font-mono text-xs text-brand-300 font-semibold">https://geomeasure-backend.onrender.com</span>
        </div>
        <div>
          <span className="text-[11px] text-surface-500 uppercase tracking-wider font-semibold block">OpenAPI Documentation</span>
          <a
            href="https://geomeasure-backend.onrender.com/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-brand-400 hover:underline flex items-center gap-1 font-medium mt-0.5"
          >
            Interactive Swagger UI ↗
          </a>
        </div>
        <div>
          <span className="text-[11px] text-surface-500 uppercase tracking-wider font-semibold block">Protocol & Format</span>
          <span className="text-xs text-surface-200 font-medium">REST API / GeoJSON & JSON</span>
        </div>
      </div>

      {/* Section 1: Authentication */}
      <div className="glass-card p-6 border border-surface-700/40 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center text-xs font-bold">1</span>
          API Key Authentication
        </h3>
        <p className="text-xs text-surface-300 leading-relaxed">
          All external API endpoints under <code className="px-1.5 py-0.5 rounded bg-surface-950 font-mono text-brand-300">/api/v1/</code> require authentication. You must supply your secret key in the <code className="px-1.5 py-0.5 rounded bg-surface-950 font-mono text-brand-300">X-API-Key</code> request header.
        </p>

        <div className="rounded-xl bg-surface-950 border border-surface-800 p-4 font-mono text-xs space-y-1">
          <div className="text-surface-500"># Preferred header format</div>
          <div className="text-emerald-400">X-API-Key: gm_live_YOUR_SECRET_KEY_HERE</div>
          <div className="text-surface-500 pt-2"># Alternative Bearer format</div>
          <div className="text-emerald-400">Authorization: Bearer gm_live_YOUR_SECRET_KEY_HERE</div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-950/70 border border-surface-800 text-xs text-surface-400 space-y-1">
          <strong className="text-surface-200">Security Invariant:</strong> API keys are generated using 256 bits of cryptographic entropy (<code className="text-brand-300 font-mono">secrets.token_urlsafe(32)</code>). The plaintext key is returned strictly once upon creation. Only a SHA-256 hash is persisted in the database.
        </div>
      </div>

      {/* Section 2: POST /api/v1/measurements/ */}
      <div className="glass-card p-6 border border-surface-700/40 space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-surface-800">
          <div className="flex items-center gap-2.5">
            <span className="px-2.5 py-1 rounded-md bg-brand-600 text-white font-mono text-xs font-bold">POST</span>
            <span className="font-mono text-sm font-semibold text-white">/api/v1/measurements/</span>
          </div>
          <span className="badge-completed text-[11px]">Protected: X-API-Key</span>
        </div>

        <p className="text-xs text-surface-300 leading-relaxed">
          Computes planar metric measurements (area in square meters, hectares, square kilometers; length in meters, kilometers) for an arbitrary GeoJSON geometry by projecting to its dynamic local UTM zone.
        </p>

        {/* Request Schema Table */}
        <div>
          <h4 className="text-xs font-semibold text-surface-200 uppercase tracking-wider mb-2">Request Body (JSON)</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-800 text-surface-400 uppercase text-[10px] tracking-wider">
                  <th className="pb-2 font-semibold">Field</th>
                  <th className="pb-2 font-semibold">Type</th>
                  <th className="pb-2 font-semibold">Required</th>
                  <th className="pb-2 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60 font-mono text-[11px]">
                <tr>
                  <td className="py-2.5 text-brand-300 font-semibold">geometry</td>
                  <td className="py-2.5 text-surface-400">Object</td>
                  <td className="py-2.5 text-emerald-400">Yes</td>
                  <td className="py-2.5 text-surface-300 font-sans">
                    Valid GeoJSON geometry object (<code className="text-surface-200">Polygon</code>, <code className="text-surface-200">MultiPolygon</code>, <code className="text-surface-200">LineString</code>, <code className="text-surface-200">MultiLineString</code>, <code className="text-surface-200">Point</code>).
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 text-brand-300 font-semibold">crs</td>
                  <td className="py-2.5 text-surface-400">String</td>
                  <td className="py-2.5 text-emerald-400">Yes</td>
                  <td className="py-2.5 text-surface-300 font-sans">
                    Coordinate Reference System of input coordinates (e.g. <code className="text-surface-200">"EPSG:4326"</code>, <code className="text-surface-200">"EPSG:3857"</code>). Unknown CRS is rejected.
                  </td>
                </tr>
                <tr>
                  <td className="py-2.5 text-brand-300 font-semibold">properties</td>
                  <td className="py-2.5 text-surface-400">Object</td>
                  <td className="py-2.5 text-surface-500">No</td>
                  <td className="py-2.5 text-surface-300 font-sans">
                    Optional dictionary of custom attributes returned alongside measurement results.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Response Schema Table */}
        <div>
          <h4 className="text-xs font-semibold text-surface-200 uppercase tracking-wider mb-2">Response Body (JSON)</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-800 text-surface-400 uppercase text-[10px] tracking-wider">
                  <th className="pb-2 font-semibold">Field</th>
                  <th className="pb-2 font-semibold">Type</th>
                  <th className="pb-2 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60 font-mono text-[11px]">
                <tr>
                  <td className="py-2 text-brand-300">geometry_type</td>
                  <td className="py-2 text-surface-400">string</td>
                  <td className="py-2 text-surface-300 font-sans">Detected geometry type (e.g. "Polygon", "LineString").</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">source_crs</td>
                  <td className="py-2 text-surface-400">string</td>
                  <td className="py-2 text-surface-300 font-sans">Input coordinate reference system specified in request.</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">measurement_crs</td>
                  <td className="py-2 text-surface-400">string</td>
                  <td className="py-2 text-surface-300 font-sans">Dynamically resolved local UTM zone projection (e.g. "EPSG:32643").</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">area_sq_meters</td>
                  <td className="py-2 text-surface-400">number | null</td>
                  <td className="py-2 text-surface-300 font-sans">Planar area in square meters (polygons only).</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">area_hectares</td>
                  <td className="py-2 text-surface-400">number | null</td>
                  <td className="py-2 text-surface-300 font-sans">Area in hectares (1 ha = 10,000 m²).</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">area_sq_km</td>
                  <td className="py-2 text-surface-400">number | null</td>
                  <td className="py-2 text-surface-300 font-sans">Area in square kilometers (1 km² = 1,000,000 m²).</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">length_meters</td>
                  <td className="py-2 text-surface-400">number | null</td>
                  <td className="py-2 text-surface-300 font-sans">Planar length in meters (linestrings only).</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">length_km</td>
                  <td className="py-2 text-surface-400">number | null</td>
                  <td className="py-2 text-surface-300 font-sans">Length in kilometers (1 km = 1,000 m).</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">measurement_unit</td>
                  <td className="py-2 text-surface-400">string</td>
                  <td className="py-2 text-surface-300 font-sans">Base unit of measurement ("meters").</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Example cURL */}
        <div>
          <h4 className="text-xs font-semibold text-surface-200 uppercase tracking-wider mb-2">Example Request</h4>
          <pre className="p-4 rounded-xl bg-surface-950 border border-surface-800 font-mono text-xs text-surface-300 overflow-x-auto leading-relaxed">
{`curl -X POST "https://geomeasure-backend.onrender.com/api/v1/measurements/" \\
  -H "X-API-Key: gm_live_YOUR_KEY_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{
    "geometry": {
      "type": "Polygon",
      "coordinates": [
        [
          [77.2090, 28.6139],
          [77.2190, 28.6139],
          [77.2190, 28.6239],
          [77.2090, 28.6239],
          [77.2090, 28.6139]
        ]
      ]
    },
    "crs": "EPSG:4326",
    "properties": {
      "parcel_name": "Commercial Zone 4B"
    }
  }'`}
          </pre>
        </div>
      </div>

      {/* Section 3: Geospatial CRS Policy */}
      <div className="glass-card p-6 border border-surface-700/40 space-y-3">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center text-xs font-bold">2</span>
          Geospatial Correctness & Projection Policy
        </h3>
        <p className="text-xs text-surface-300 leading-relaxed">
          GeoMeasure Studio implements strict geospatial computation standards:
        </p>
        <ul className="space-y-2 text-xs text-surface-400 list-disc list-inside">
          <li>
            <strong className="text-surface-200">No Degrees as Distance:</strong> Euclidean area/distance calculations on geographic degree coordinates (<code className="text-brand-300 font-mono">EPSG:4326</code>) are mathematically invalid because degree lengths vary with latitude.
          </li>
          <li>
            <strong className="text-surface-200">Dynamic UTM Reprojection:</strong> Every geometry submitted in geographic coordinates is reprojected to the appropriate local Universal Transverse Mercator (UTM) zone matching its centroid coordinates prior to planar metric computation.
          </li>
          <li>
            <strong className="text-surface-200">Strict Unknown CRS Policy:</strong> Submissions with missing, unknown, or unverifiable coordinate systems are rejected with HTTP 400. GeoMeasure Studio never silently guesses unknown coordinate systems.
          </li>
        </ul>
      </div>

      {/* Section 4: HTTP Status Codes & Error Handling */}
      <div className="glass-card p-6 border border-surface-700/40 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center text-xs font-bold">3</span>
          HTTP Status Codes & Error Reference
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-surface-800 text-surface-400 uppercase text-[10px] tracking-wider">
                <th className="pb-2 font-semibold">Status Code</th>
                <th className="pb-2 font-semibold">Scenario</th>
                <th className="pb-2 font-semibold">Response Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-800/60 font-mono text-[11px]">
              <tr>
                <td className="py-2.5 text-emerald-400 font-bold">200 OK</td>
                <td className="py-2.5 text-surface-300 font-sans">Geometry successfully parsed and measured.</td>
                <td className="py-2.5 text-surface-400">Measurement object with metric values.</td>
              </tr>
              <tr>
                <td className="py-2.5 text-rose-400 font-bold">401 Unauthorized</td>
                <td className="py-2.5 text-surface-300 font-sans">Missing, invalid, malformed, revoked, or expired API key.</td>
                <td className="py-2.5 text-surface-400">"API key has been revoked and can no longer be used."</td>
              </tr>
              <tr>
                <td className="py-2.5 text-amber-400 font-bold">400 Bad Request</td>
                <td className="py-2.5 text-surface-300 font-sans">Malformed GeoJSON coordinates or unknown CRS submitted.</td>
                <td className="py-2.5 text-surface-400">"An explicit, valid Coordinate Reference System (CRS) is required."</td>
              </tr>
              <tr>
                <td className="py-2.5 text-rose-400 font-bold">404 Not Found</td>
                <td className="py-2.5 text-surface-300 font-sans">Attempting to inspect or revoke a key not owned by authenticated user.</td>
                <td className="py-2.5 text-surface-400">"API key not found."</td>
              </tr>
              <tr>
                <td className="py-2.5 text-red-500 font-bold">500 Internal Error</td>
                <td className="py-2.5 text-surface-300 font-sans">Transient database error or server misconfiguration.</td>
                <td className="py-2.5 text-surface-400">"Measurement calculation failed."</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
