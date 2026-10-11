/* ======================================================
   GeoMeasure Studio — Developer Overview Tab
   Metrics, Usage Summary, and Quick Actions
   ====================================================== */

import React from 'react';
import type { ApiKeyMetadata } from '../../types';

interface OverviewTabProps {
  keys: ApiKeyMetadata[];
  loading: boolean;
  onCreateKeyClick: () => void;
  onNavigateToPlayground: () => void;
  onNavigateToDocs: () => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  keys,
  loading,
  onCreateKeyClick,
  onNavigateToPlayground,
  onNavigateToDocs,
}) => {
  // Compute real metrics from loaded user keys
  const totalKeys = keys.length;
  const activeKeys = keys.filter((k) => k.is_active).length;
  const revokedOrExpiredKeys = keys.filter((k) => !k.is_active).length;
  const totalRequests = keys.reduce((acc, k) => acc + (k.request_count || 0), 0);

  const recentKeys = [...keys].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  }).slice(0, 4);

  return (
    <div className="space-y-6">
      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Keys */}
        <div className="glass-card p-5 border border-surface-700/40 relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-surface-400 uppercase tracking-wider">Total Keys</span>
            <div className="w-8 h-8 rounded-lg bg-brand-500/10 text-brand-400 flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
          </div>
          <div className="text-2xl font-bold text-white tracking-tight">
            {loading ? <span className="text-surface-600 animate-pulse">...</span> : totalKeys}
          </div>
          <p className="text-[11px] text-surface-500 mt-1">Credentials owned by account</p>
        </div>

        {/* Active Keys */}
        <div className="glass-card p-5 border border-surface-700/40 relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-surface-400 uppercase tracking-wider">Active Keys</span>
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
          <div className="text-2xl font-bold text-emerald-400 tracking-tight">
            {loading ? <span className="text-surface-600 animate-pulse">...</span> : activeKeys}
          </div>
          <p className="text-[11px] text-surface-500 mt-1">Authorized for API calls</p>
        </div>

        {/* Inactive / Revoked */}
        <div className="glass-card p-5 border border-surface-700/40 relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-surface-400 uppercase tracking-wider">Revoked / Expired</span>
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
              </svg>
            </div>
          </div>
          <div className="text-2xl font-bold text-rose-400 tracking-tight">
            {loading ? <span className="text-surface-600 animate-pulse">...</span> : revokedOrExpiredKeys}
          </div>
          <p className="text-[11px] text-surface-500 mt-1">Access immediately blocked</p>
        </div>

        {/* Total API Requests */}
        <div className="glass-card p-5 border border-surface-700/40 relative overflow-hidden">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-surface-400 uppercase tracking-wider">Total Requests</span>
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-400 flex items-center justify-center">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
          </div>
          <div className="text-2xl font-bold text-indigo-300 tracking-tight">
            {loading ? <span className="text-surface-600 animate-pulse">...</span> : totalRequests.toLocaleString()}
          </div>
          <p className="text-[11px] text-surface-500 mt-1">Real database usage counter</p>
        </div>
      </div>

      {/* Quick Actions & Quick Start */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Quick Actions Card */}
        <div className="lg:col-span-5 glass-card p-6 border border-surface-700/40 flex flex-col justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white mb-1.5 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
              Developer Quick Actions
            </h3>
            <p className="text-xs text-surface-400 mb-5">
              Generate credentials, test geospatial payloads in the interactive sandbox, or explore endpoint schemas.
            </p>

            <div className="space-y-2.5">
              <button
                onClick={onCreateKeyClick}
                className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-brand-600 to-indigo-600 hover:from-brand-500 hover:to-indigo-500 text-white font-medium text-xs flex items-center justify-between shadow-lg shadow-brand-600/20 transition active:scale-[0.98]"
              >
                <span className="flex items-center gap-2.5">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Generate New API Key
                </span>
                <span className="text-white/60 text-[11px]">&rarr;</span>
              </button>

              <button
                onClick={onNavigateToPlayground}
                className="w-full py-2.5 px-4 rounded-xl bg-surface-800/90 hover:bg-surface-800 text-surface-200 border border-surface-700/60 font-medium text-xs flex items-center justify-between transition active:scale-[0.98]"
              >
                <span className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Launch API Playground
                </span>
                <span className="text-surface-500 text-[11px]">&rarr;</span>
              </button>

              <button
                onClick={onNavigateToDocs}
                className="w-full py-2.5 px-4 rounded-xl bg-surface-800/90 hover:bg-surface-800 text-surface-200 border border-surface-700/60 font-medium text-xs flex items-center justify-between transition active:scale-[0.98]"
              >
                <span className="flex items-center gap-2.5">
                  <svg className="w-4 h-4 text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                  API Reference & Schemas
                </span>
                <span className="text-surface-500 text-[11px]">&rarr;</span>
              </button>
            </div>
          </div>

          <div className="mt-6 p-3 rounded-xl bg-surface-950/70 border border-surface-800 text-[11px] text-surface-400">
            <span className="font-semibold text-surface-300">Architecture Note:</span> Request counters are updated atomically on every API call. Historical time-series charts will be introduced in Phase 3.
          </div>
        </div>

        {/* Quick cURL Integration */}
        <div className="lg:col-span-7 glass-card p-6 border border-surface-700/40 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                <span className="px-2 py-0.5 rounded bg-brand-500/20 text-brand-300 font-mono text-[10px] font-bold">POST</span>
                External Measurement API
              </h3>
              <span className="text-[11px] text-surface-500 font-mono">/api/v1/measurements/</span>
            </div>
            <p className="text-xs text-surface-400 mb-4">
              Submit any GeoJSON geometry with an explicit CRS to compute planar metric measurements via dynamic local UTM projection.
            </p>

            <div className="relative rounded-xl bg-surface-950 border border-surface-800 p-4 font-mono text-[11px] text-surface-300 overflow-x-auto">
              <div className="text-surface-500 mb-1"># Authenticate with X-API-Key header</div>
              <span className="text-brand-400">curl</span> -X POST <span className="text-emerald-400">"https://geomeasure-backend.onrender.com/api/v1/measurements/"</span> \{"\n"}
              {"  "}-H <span className="text-emerald-400">"X-API-Key: gm_live_YOUR_KEY_HERE"</span> \{"\n"}
              {"  "}-H <span className="text-emerald-400">"Content-Type: application/json"</span> \{"\n"}
              {"  "}-d <span className="text-amber-300">'{`{
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[77.209, 28.613], [77.219, 28.613], [77.219, 28.623], [77.209, 28.613]]]
    },
    "crs": "EPSG:4326"
  }`}'</span>
            </div>
          </div>

          <div className="mt-4 flex items-center justify-between text-xs text-surface-400">
            <span className="flex items-center gap-1.5 text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              Dynamic Local UTM Reprojection
            </span>
            <button
              onClick={onNavigateToPlayground}
              className="text-brand-400 hover:text-brand-300 font-medium text-xs flex items-center gap-1 transition"
            >
              Test in Sandbox &rarr;
            </button>
          </div>
        </div>
      </div>

      {/* Recent Keys Activity Table */}
      <div className="glass-card p-6 border border-surface-700/40">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent Credentials</h3>
            <p className="text-xs text-surface-400">Latest active and revoked keys associated with this account</p>
          </div>
          <button
            onClick={onCreateKeyClick}
            className="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            New Key
          </button>
        </div>

        {loading ? (
          <div className="py-8 text-center text-surface-500 text-xs flex items-center justify-center gap-2">
            <div className="w-4 h-4 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
            <span>Loading credentials...</span>
          </div>
        ) : recentKeys.length === 0 ? (
          <div className="py-10 text-center text-surface-500 text-xs space-y-2">
            <p>No API keys generated yet.</p>
            <button
              onClick={onCreateKeyClick}
              className="text-brand-400 hover:underline font-medium"
            >
              Generate your first key to start making programmatic API calls
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-800 text-surface-400 uppercase text-[10px] tracking-wider">
                  <th className="pb-3 font-semibold">Key Name</th>
                  <th className="pb-3 font-semibold">Identifier Prefix</th>
                  <th className="pb-3 font-semibold">Status</th>
                  <th className="pb-3 font-semibold">Total Calls</th>
                  <th className="pb-3 font-semibold">Last Used</th>
                  <th className="pb-3 font-semibold">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60">
                {recentKeys.map((k) => (
                  <tr key={k.id} className="hover:bg-surface-800/20 transition-colors">
                    <td className="py-3 font-medium text-white">{k.name}</td>
                    <td className="py-3 font-mono text-surface-300 text-[11px]">{k.prefix}...</td>
                    <td className="py-3">
                      {k.is_active ? (
                        <span className="badge-completed">Active</span>
                      ) : k.revoked_at ? (
                        <span className="badge-error">Revoked</span>
                      ) : (
                        <span className="badge-processing">Expired</span>
                      )}
                    </td>
                    <td className="py-3 font-mono text-surface-300">
                      {(k.request_count || 0).toLocaleString()}
                    </td>
                    <td className="py-3 text-surface-400 text-[11px]">
                      {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never used'}
                    </td>
                    <td className="py-3 text-surface-400 text-[11px]">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
