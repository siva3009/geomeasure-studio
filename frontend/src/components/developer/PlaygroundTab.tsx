/* ======================================================
   GeoMeasure Studio — API Playground Tab
   Interactive Sandbox for POST /api/v1/measurements/
   ====================================================== */

import React, { useState } from 'react';
import type {
  ApiKeyMetadata,
  PlaygroundExecutionResult,
  GeometryMeasurementResponse,
} from '../../types';
import { testMeasurementPlayground } from '../../api/client';

interface PlaygroundTabProps {
  keys: ApiKeyMetadata[];
}

const PRESET_POLYGON = {
  type: 'Polygon',
  coordinates: [
    [
      [77.2090, 28.6139],
      [77.2190, 28.6139],
      [77.2190, 28.6239],
      [77.2090, 28.6239],
      [77.2090, 28.6139],
    ],
  ],
};

const PRESET_LINESTRING = {
  type: 'LineString',
  coordinates: [
    [77.2090, 28.6139],
    [77.2140, 28.6189],
    [77.2190, 28.6239],
  ],
};

const PRESET_POINT = {
  type: 'Point',
  coordinates: [77.2090, 28.6139],
};

export const PlaygroundTab: React.FC<PlaygroundTabProps> = ({ keys }) => {
  const activeKeys = keys.filter((k) => k.is_active);

  // Playground form state
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [maskApiKey, setMaskApiKey] = useState(true);
  const [selectedPreset, setSelectedPreset] = useState<'polygon' | 'linestring' | 'point' | 'custom'>('polygon');
  const [geometryJson, setGeometryJson] = useState(JSON.stringify(PRESET_POLYGON, null, 2));
  const [crsInput, setCrsInput] = useState('EPSG:4326');
  const [propertiesJson, setPropertiesJson] = useState('{\n  "parcel_id": "Plot-4A",\n  "zone": "North"\n}');

  // Execution states
  const [executing, setExecuting] = useState(false);
  const [result, setResult] = useState<PlaygroundExecutionResult | null>(null);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [copiedCurl, setCopiedCurl] = useState(false);
  const [copiedResponse, setCopiedResponse] = useState(false);

  const handlePresetSelect = (preset: 'polygon' | 'linestring' | 'point' | 'custom') => {
    setSelectedPreset(preset);
    setJsonError(null);
    if (preset === 'polygon') {
      setGeometryJson(JSON.stringify(PRESET_POLYGON, null, 2));
    } else if (preset === 'linestring') {
      setGeometryJson(JSON.stringify(PRESET_LINESTRING, null, 2));
    } else if (preset === 'point') {
      setGeometryJson(JSON.stringify(PRESET_POINT, null, 2));
    }
  };

  const handleFormatJson = () => {
    try {
      const parsed = JSON.parse(geometryJson);
      setGeometryJson(JSON.stringify(parsed, null, 2));
      setJsonError(null);
    } catch (e: unknown) {
      setJsonError(e instanceof Error ? e.message : 'Invalid JSON syntax');
    }
  };

  const handleSendRequest = async () => {
    setJsonError(null);
    if (!apiKeyInput.trim()) {
      setJsonError('Please enter an API key (e.g. gm_live_...) to test the endpoint.');
      return;
    }

    let parsedGeometry: Record<string, unknown>;
    try {
      parsedGeometry = JSON.parse(geometryJson);
    } catch (e: unknown) {
      setJsonError(`Invalid Geometry JSON: ${e instanceof Error ? e.message : 'Syntax error'}`);
      return;
    }

    let parsedProperties: Record<string, unknown> | undefined;
    if (propertiesJson.trim()) {
      try {
        parsedProperties = JSON.parse(propertiesJson);
      } catch (e: unknown) {
        setJsonError(`Invalid Properties JSON: ${e instanceof Error ? e.message : 'Syntax error'}`);
        return;
      }
    }

    setExecuting(true);
    setResult(null);
    try {
      const res = await testMeasurementPlayground(
        {
          geometry: parsedGeometry,
          crs: crsInput.trim() || 'EPSG:4326',
          properties: parsedProperties,
        },
        apiKeyInput.trim()
      );
      setResult(res);
    } catch (err: unknown) {
      setResult({
        status: 500,
        statusText: 'Client Error',
        durationMs: 0,
        data: { detail: err instanceof Error ? err.message : 'Network execution failed' },
        error: err instanceof Error ? err.message : 'Network error',
      });
    } finally {
      setExecuting(false);
    }
  };

  // Generate dynamic curl command
  const cleanKey = apiKeyInput.trim() || 'gm_live_YOUR_KEY_HERE';
  const curlKeyDisplay = maskApiKey && apiKeyInput.trim()
    ? `${apiKeyInput.trim().slice(0, 10)}••••••••••••••••`
    : cleanKey;

  const curlCommand = `curl -X POST "https://geomeasure-backend.onrender.com/api/v1/measurements/" \\
  -H "X-API-Key: ${cleanKey}" \\
  -H "Content-Type: application/json" \\
  -d '${JSON.stringify(
    {
      geometry: (() => {
        try {
          return JSON.parse(geometryJson);
        } catch {
          return PRESET_POLYGON;
        }
      })(),
      crs: crsInput.trim() || 'EPSG:4326',
      ...(propertiesJson.trim()
        ? (() => {
            try {
              return { properties: JSON.parse(propertiesJson) };
            } catch {
              return {};
            }
          })()
        : {}),
    },
    null,
    2
  )}'`;

  const handleCopyCurl = async () => {
    try {
      await navigator.clipboard.writeText(curlCommand);
      setCopiedCurl(true);
      setTimeout(() => setCopiedCurl(false), 2500);
    } catch (err) {
      console.error('Failed to copy curl:', err);
    }
  };

  const handleCopyResponse = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(result.data, null, 2));
      setCopiedResponse(true);
      setTimeout(() => setCopiedResponse(false), 2500);
    } catch (err) {
      console.error('Failed to copy response:', err);
    }
  };

  const measurementData = result?.status === 200
    ? (result.data as GeometryMeasurementResponse)
    : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-base font-semibold text-white flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
          Interactive API Playground
        </h2>
        <p className="text-xs text-surface-400">
          Execute real requests against <code className="px-1.5 py-0.5 rounded bg-surface-900 text-cyan-300 font-mono text-[11px]">POST /api/v1/measurements/</code> with actual credentials.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Request Builder */}
        <div className="lg:col-span-6 space-y-5">
          {/* 1. API Key Selector Card */}
          <div className="glass-card p-5 border border-surface-700/40 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-surface-300 uppercase tracking-wider">
                1. API Key Authentication
              </label>
              <button
                type="button"
                onClick={() => setMaskApiKey(!maskApiKey)}
                className="text-[11px] text-brand-400 hover:text-brand-300 transition"
              >
                {maskApiKey ? 'Show Secret' : 'Mask Secret'}
              </button>
            </div>

            {activeKeys.length > 0 && (
              <div>
                <span className="text-[11px] text-surface-400 mb-1 block">Active Keys in Account:</span>
                <div className="flex flex-wrap gap-1.5">
                  {activeKeys.map((k) => (
                    <span
                      key={k.id}
                      className="px-2 py-0.5 rounded-lg bg-surface-950 border border-surface-800 text-[11px] font-mono text-surface-300"
                    >
                      {k.name} ({k.prefix}...)
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div>
              <input
                type={maskApiKey ? 'password' : 'text'}
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
                placeholder="Paste key: gm_live_..."
                className="w-full px-3.5 py-2.5 rounded-xl bg-surface-950 border border-surface-700/60 text-white font-mono text-xs placeholder:text-surface-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
              />
              <p className="text-[11px] text-surface-500 mt-1">
                Supplied via <code className="text-surface-400 font-mono">X-API-Key</code> header. Key is held only in component memory during testing.
              </p>
            </div>
          </div>

          {/* 2. Payload Builder Card */}
          <div className="glass-card p-5 border border-surface-700/40 space-y-4">
            <div className="flex items-center justify-between">
              <label className="text-xs font-semibold text-surface-300 uppercase tracking-wider">
                2. Geometry & CRS Input
              </label>
              <div className="flex items-center gap-1 bg-surface-950 p-0.5 rounded-lg border border-surface-800">
                {(['polygon', 'linestring', 'point', 'custom'] as const).map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => handlePresetSelect(preset)}
                    className={`px-2 py-1 text-[11px] font-medium rounded-md capitalize transition ${
                      selectedPreset === preset
                        ? 'bg-brand-600 text-white shadow-sm'
                        : 'text-surface-400 hover:text-surface-200'
                    }`}
                  >
                    {preset}
                  </button>
                ))}
              </div>
            </div>

            {/* Geometry JSON editor */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-medium text-surface-400">GeoJSON Geometry Object</span>
                <button
                  type="button"
                  onClick={handleFormatJson}
                  className="text-[11px] text-surface-400 hover:text-surface-200 transition"
                >
                  Format JSON
                </button>
              </div>
              <textarea
                rows={7}
                value={geometryJson}
                onChange={(e) => {
                  setGeometryJson(e.target.value);
                  setSelectedPreset('custom');
                }}
                className="w-full p-3 rounded-xl bg-surface-950 border border-surface-700/60 font-mono text-xs text-surface-200 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
                spellCheck={false}
              />
            </div>

            {/* CRS Input */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-surface-400 mb-1">
                  Coordinate Reference System (CRS)
                </label>
                <input
                  type="text"
                  value={crsInput}
                  onChange={(e) => setCrsInput(e.target.value)}
                  placeholder="EPSG:4326"
                  className="w-full px-3 py-2 rounded-xl bg-surface-950 border border-surface-700/60 text-white font-mono text-xs focus:outline-none focus:border-brand-500"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-surface-400 mb-1">
                  Quick CRS Presets
                </label>
                <div className="flex items-center gap-1.5 pt-0.5">
                  {['EPSG:4326', 'EPSG:3857', 'EPSG:32643'].map((crs) => (
                    <button
                      key={crs}
                      type="button"
                      onClick={() => setCrsInput(crs)}
                      className={`px-2 py-1 rounded text-[10px] font-mono border transition ${
                        crsInput === crs
                          ? 'bg-brand-500/20 text-brand-300 border-brand-500/40'
                          : 'bg-surface-950 text-surface-400 border-surface-800 hover:text-surface-200'
                      }`}
                    >
                      {crs}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Optional Properties */}
            <div>
              <span className="text-xs font-medium text-surface-400 mb-1 block">
                Feature Properties (Optional JSON metadata)
              </span>
              <textarea
                rows={3}
                value={propertiesJson}
                onChange={(e) => setPropertiesJson(e.target.value)}
                className="w-full p-2.5 rounded-xl bg-surface-950 border border-surface-700/60 font-mono text-xs text-surface-300 focus:outline-none focus:border-brand-500"
                spellCheck={false}
              />
            </div>

            {jsonError && (
              <div className="p-3 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-200 text-xs flex items-start gap-2">
                <svg className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{jsonError}</span>
              </div>
            )}

            <button
              type="button"
              disabled={executing}
              onClick={handleSendRequest}
              className="w-full py-3 btn-primary text-xs font-semibold flex items-center justify-center gap-2 shadow-lg shadow-brand-600/30"
            >
              {executing ? (
                <>
                  <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  <span>Executing API Request...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                  <span>Send Request</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Execution Output & cURL */}
        <div className="lg:col-span-6 space-y-5">
          {/* Response Inspector Card */}
          <div className="glass-card p-5 border border-surface-700/40 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-surface-800">
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-semibold text-surface-300 uppercase tracking-wider">Response Output</span>
                {result && (
                  <span
                    className={`badge text-xs font-mono font-bold ${
                      result.status === 200
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                        : result.status === 401
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                        : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    }`}
                  >
                    HTTP {result.status} {result.statusText}
                  </span>
                )}
              </div>
              {result && (
                <div className="flex items-center gap-2">
                  <span className="text-[11px] font-mono text-surface-400 bg-surface-950 px-2 py-0.5 rounded border border-surface-800">
                    {result.durationMs} ms
                  </span>
                  <button
                    onClick={handleCopyResponse}
                    className="btn-ghost text-[11px] py-1 px-2"
                  >
                    {copiedResponse ? 'Copied!' : 'Copy'}
                  </button>
                </div>
              )}
            </div>

            {/* If 200 OK, display computed measurement highlights */}
            {measurementData && (
              <div className="p-3.5 rounded-xl bg-surface-950 border border-emerald-500/30 space-y-2.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-white flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400" />
                    Geometry: {measurementData.geometry_type}
                  </span>
                  <span className="font-mono text-[11px] text-brand-300">
                    UTM CRS: {measurementData.measurement_crs || 'N/A'}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-1 text-xs">
                  {measurementData.area_sq_meters !== null && (
                    <div className="p-2 rounded-lg bg-surface-900 border border-surface-800">
                      <span className="text-[10px] text-surface-400 block">Area (m²)</span>
                      <span className="font-mono font-semibold text-emerald-300">
                        {measurementData.area_sq_meters.toLocaleString()} m²
                      </span>
                    </div>
                  )}
                  {measurementData.area_hectares !== null && (
                    <div className="p-2 rounded-lg bg-surface-900 border border-surface-800">
                      <span className="text-[10px] text-surface-400 block">Area (Hectares)</span>
                      <span className="font-mono font-semibold text-emerald-300">
                        {measurementData.area_hectares.toLocaleString()} ha
                      </span>
                    </div>
                  )}
                  {measurementData.length_meters !== null && (
                    <div className="p-2 rounded-lg bg-surface-900 border border-surface-800">
                      <span className="text-[10px] text-surface-400 block">Length (m)</span>
                      <span className="font-mono font-semibold text-cyan-300">
                        {measurementData.length_meters.toLocaleString()} m
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error Guidance if 401 or 400 */}
            {result && result.status !== 200 && (
              <div className="p-3 rounded-xl bg-surface-950 border border-surface-800 text-xs space-y-1">
                <span className="font-semibold text-rose-300">Troubleshooting Guidance:</span>
                <p className="text-[11px] text-surface-400">
                  {result.status === 401
                    ? 'Authentication rejected. Verify that your API key starts with gm_live_, has not expired, and has not been revoked.'
                    : result.status === 400
                    ? 'Validation error. Ensure the geometry coordinates form a valid GeoJSON structure and the CRS is an identifiable EPSG code.'
                    : 'Server error encountered during request execution.'}
                </p>
              </div>
            )}

            {/* Raw JSON View */}
            <div className="relative">
              <pre className="p-3.5 rounded-xl bg-surface-950 border border-surface-800 font-mono text-[11px] text-surface-200 overflow-x-auto max-h-[340px]">
                {result ? (
                  JSON.stringify(result.data, null, 2)
                ) : (
                  <span className="text-surface-600">// Press "Send Request" to view live response output</span>
                )}
              </pre>
            </div>
          </div>

          {/* cURL Code Snippet Card */}
          <div className="glass-card p-5 border border-surface-700/40 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-surface-300 uppercase tracking-wider">
                Equivalent cURL Command
              </span>
              <button
                type="button"
                onClick={handleCopyCurl}
                className="btn-ghost text-[11px] py-1 px-2.5 flex items-center gap-1 text-brand-300 hover:text-brand-200"
              >
                {copiedCurl ? (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                    </svg>
                    <span>Copy cURL</span>
                  </>
                )}
              </button>
            </div>

            <pre className="p-3.5 rounded-xl bg-surface-950 border border-surface-800 font-mono text-[11px] text-surface-300 overflow-x-auto leading-relaxed">
              {`curl -X POST "https://geomeasure-backend.onrender.com/api/v1/measurements/" \\
  -H "X-API-Key: ${curlKeyDisplay}" \\
  -H "Content-Type: application/json" \\
  -d '{
    "geometry": ${JSON.stringify(
      (() => {
        try {
          return JSON.parse(geometryJson);
        } catch {
          return PRESET_POLYGON;
        }
      })()
    )},
    "crs": "${crsInput.trim() || 'EPSG:4326'}"
  }'`}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
