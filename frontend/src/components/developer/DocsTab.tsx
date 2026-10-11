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

      {/* Section 3: API Rate Limiting & Monthly Quotas */}
      <div className="glass-card p-6 border border-surface-700/40 space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-surface-800">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center text-xs font-bold">2</span>
            API Rate Limiting & Tier Quotas
          </h3>
          <span className="badge-completed text-[11px]">Sliding Window Enforcement</span>
        </div>

        <p className="text-xs text-surface-300 leading-relaxed">
          GeoMeasure Studio implements server-side sliding-window rate limiting and transactional monthly quotas per API key. Limits are enforced automatically without impacting public file uploads.
        </p>

        {/* Tier Allowance Table */}
        <div>
          <h4 className="text-xs font-semibold text-surface-200 uppercase tracking-wider mb-2">Service Tiers & Limits</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-800 text-surface-400 uppercase text-[10px] tracking-wider">
                  <th className="pb-2 font-semibold">Tier Plan</th>
                  <th className="pb-2 font-semibold">Rate Limit</th>
                  <th className="pb-2 font-semibold">Monthly Quota</th>
                  <th className="pb-2 font-semibold">Reset Boundary</th>
                  <th className="pb-2 font-semibold">Target Environment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60 font-mono text-[11px]">
                <tr>
                  <td className="py-2.5 text-brand-300 font-semibold">development</td>
                  <td className="py-2.5 text-surface-300">10 requests / min</td>
                  <td className="py-2.5 text-surface-300">1,000 requests</td>
                  <td className="py-2.5 text-surface-400">1st of month (00:00 UTC)</td>
                  <td className="py-2.5 text-surface-400 font-sans">Testing, SDK exploration & local pipelines</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-brand-300 font-semibold">standard</td>
                  <td className="py-2.5 text-surface-300">60 requests / min</td>
                  <td className="py-2.5 text-surface-300">25,000 requests</td>
                  <td className="py-2.5 text-surface-400">1st of month (00:00 UTC)</td>
                  <td className="py-2.5 text-surface-400 font-sans">Production applications & medium-volume workflows</td>
                </tr>
                <tr>
                  <td className="py-2.5 text-brand-300 font-semibold">higher-volume</td>
                  <td className="py-2.5 text-surface-300">120 requests / min</td>
                  <td className="py-2.5 text-surface-300">100,000 requests</td>
                  <td className="py-2.5 text-surface-400">1st of month (00:00 UTC)</td>
                  <td className="py-2.5 text-surface-400 font-sans">Automated batch ingestion & heavy enterprise feeds</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Response Headers */}
        <div>
          <h4 className="text-xs font-semibold text-surface-200 uppercase tracking-wider mb-2">Standard Rate Limit Response Headers</h4>
          <p className="text-xs text-surface-400 mb-2">
            Every response from <code className="text-brand-300 font-mono">/api/v1/measurements/</code> includes the following headers to help clients pace their requests:
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-800 text-surface-400 uppercase text-[10px] tracking-wider">
                  <th className="pb-2 font-semibold">Header</th>
                  <th className="pb-2 font-semibold">Type</th>
                  <th className="pb-2 font-semibold">Definition</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60 font-mono text-[11px]">
                <tr>
                  <td className="py-2 text-brand-300">X-RateLimit-Limit</td>
                  <td className="py-2 text-surface-400">Integer</td>
                  <td className="py-2 text-surface-300 font-sans">Maximum permitted requests per 60-second window for the API key's tier.</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">X-RateLimit-Remaining</td>
                  <td className="py-2 text-surface-400">Integer</td>
                  <td className="py-2 text-surface-300 font-sans">Remaining requests permitted in the current 60-second sliding window.</td>
                </tr>
                <tr>
                  <td className="py-2 text-brand-300">X-RateLimit-Reset</td>
                  <td className="py-2 text-surface-400">Integer</td>
                  <td className="py-2 text-surface-300 font-sans">Unix epoch timestamp (seconds) when the sliding window clears the oldest request.</td>
                </tr>
                <tr>
                  <td className="py-2 text-amber-400">Retry-After</td>
                  <td className="py-2 text-surface-400">Integer</td>
                  <td className="py-2 text-surface-300 font-sans">Included on HTTP 429 responses. Number of seconds the client must wait before retrying.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* 429 Format */}
        <div>
          <h4 className="text-xs font-semibold text-surface-200 uppercase tracking-wider mb-2">HTTP 429 Error Response Format</h4>
          <pre className="p-4 rounded-xl bg-surface-950 border border-surface-800 font-mono text-xs text-surface-300 overflow-x-auto leading-relaxed">
{`HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1775920060
Retry-After: 42
Content-Type: application/json

{
  "detail": "Rate limit exceeded. Try again in 42 seconds.",
  "reason": "rate_limit_exceeded",
  "retry_after": 42
}`}
          </pre>
        </div>

        {/* How to test locally */}
        <div className="p-4 rounded-xl bg-surface-950/70 border border-surface-800 space-y-2 text-xs">
          <h5 className="font-semibold text-surface-200 flex items-center gap-1.5">
            <svg className="w-4 h-4 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Testing Rate Limits Locally or via Shell
          </h5>
          <p className="text-surface-400 leading-relaxed">
            Generate an API key on the <strong className="text-surface-300">Development</strong> tier (10 req/min). Run the following bash loop to observe the rate limiter trigger and verify the <code className="text-brand-300 font-mono">429</code> response with headers:
          </p>
          <pre className="p-3 rounded-lg bg-surface-950 border border-surface-800 font-mono text-[11px] text-surface-300 overflow-x-auto">
{`for i in {1..12}; do
  curl -s -i -X POST "http://localhost:8000/api/v1/measurements/" \\
    -H "X-API-Key: YOUR_DEV_KEY" \\
    -H "Content-Type: application/json" \\
    -d '{"geometry":{"type":"Point","coordinates":[77.2,28.6]},"crs":"EPSG:4326"}' \\
    | head -n 1
done`}
          </pre>
        </div>
      </div>

      {/* Section 4: Usage Analytics & Telemetry */}
      <div className="glass-card p-6 border border-surface-700/40 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center text-xs font-bold">3</span>
          Usage Telemetry & Analytics Endpoints
        </h3>
        <p className="text-xs text-surface-300 leading-relaxed">
          GeoMeasure Studio records operational telemetry for every authenticated external API request without storing secrets or user geometry coordinates. Telemetry can be queried via authenticated endpoints:
        </p>

        <div className="space-y-3 font-mono text-xs">
          <div className="p-3.5 rounded-xl bg-surface-950 border border-surface-800 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-bold">GET</span>
              <span className="text-white font-semibold">/api/keys/usage/summary/</span>
            </div>
            <p className="text-[11px] text-surface-400 font-sans">
              Returns aggregated quota consumption, total monthly/daily calls, success/error rates, endpoint breakdowns, and recent event logs scoped strictly to the authenticated user's keys.
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-surface-950 border border-surface-800 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="px-2 py-0.5 rounded bg-emerald-600/20 text-emerald-400 border border-emerald-500/30 text-[10px] font-bold">GET</span>
              <span className="text-white font-semibold">/api/keys/&#123;key_id&#125;/analytics/</span>
            </div>
            <p className="text-[11px] text-surface-400 font-sans">
              Detailed event history and time-series metrics for a specific key. Enforces backend ownership validation.
            </p>
          </div>
        </div>

        <div className="p-3.5 rounded-xl bg-surface-950/70 border border-surface-800 text-xs text-surface-400 space-y-1">
          <strong className="text-surface-200">Data Retention & Privacy:</strong> Usage events are retained for 90 days by default (<code className="text-brand-300 font-mono">USAGE_EVENT_RETENTION_DAYS</code>). The database stores only normalized route paths, HTTP methods, status codes, duration in milliseconds, and rejection reasons. No raw geometry, features, or credentials are ever recorded.
        </div>
      </div>

      {/* Section 5: Geospatial CRS Policy */}
      <div className="glass-card p-6 border border-surface-700/40 space-y-3">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center text-xs font-bold">4</span>
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

      {/* Section 6: HTTP Status Codes & Error Handling */}
      <div className="glass-card p-6 border border-surface-700/40 space-y-4">
        <h3 className="text-sm font-semibold text-white flex items-center gap-2">
          <span className="w-6 h-6 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center text-xs font-bold">5</span>
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
                <td className="py-2.5 text-amber-400 font-bold">429 Too Many Requests</td>
                <td className="py-2.5 text-surface-300 font-sans">Per-minute rate limit exceeded or monthly quota exhausted.</td>
                <td className="py-2.5 text-surface-400">"Rate limit exceeded. Try again in 42 seconds." with Retry-After header.</td>
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
