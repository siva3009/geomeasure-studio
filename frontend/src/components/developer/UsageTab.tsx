/* ======================================================
   GeoMeasure Studio — Developer Usage & Analytics Tab
   Rate Limiting, Quotas, and Live Request Telemetry
   ====================================================== */

import React, { useState } from 'react';
import type { UsageSummary, ApiKeyMetadata } from '../../types';

interface UsageTabProps {
  summary: UsageSummary | null;
  keys: ApiKeyMetadata[];
  loading: boolean;
  onRefresh: () => void;
  onNavigateToPlayground?: () => void;
}

export const UsageTab: React.FC<UsageTabProps> = ({
  summary,
  keys,
  loading,
  onRefresh,
  onNavigateToPlayground,
}) => {
  const [selectedKeyFilter, setSelectedKeyFilter] = useState<string>('all');

  if (!summary && loading) {
    return (
      <div className="flex flex-col items-center justify-center p-16 space-y-4">
        <div className="w-8 h-8 border-3 border-brand-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-surface-400">Loading live usage analytics...</p>
      </div>
    );
  }

  const quotaPercent = summary && summary.monthly_quota_limit > 0
    ? Math.min(100, Math.round((summary.requests_this_month / summary.monthly_quota_limit) * 100))
    : 0;

  const isQuotaCritical = quotaPercent >= 90;
  const isQuotaExhausted = summary ? summary.monthly_quota_remaining === 0 : false;

  // Filter recent activity if key filter is chosen
  const filteredActivity = (summary?.recent_activity ?? []).filter((item) => {
    if (selectedKeyFilter === 'all') return true;
    return item.api_key_id === selectedKeyFilter;
  });

  // Calculate maximum for daily usage SVG bars
  const maxDailyCount = Math.max(
    1,
    ...(summary?.daily_usage ?? []).map((d) => d.count)
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">Usage & Rate Limits</h2>
          <p className="text-xs text-surface-400">
            Real-time request metrics, quota consumption, and telemetry for your API credentials.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
            title="Refresh usage telemetry"
          >
            <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Quota Exhaustion / Warning Banner */}
      {isQuotaExhausted ? (
        <div className="p-4 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-200 text-xs flex items-start gap-3">
          <svg className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <span className="font-semibold text-rose-300 block text-sm">Monthly Quota Exhausted (100%)</span>
            <p className="mt-1 text-rose-200/90 text-xs leading-relaxed">
              Your API requests have reached the monthly quota limit ({summary?.monthly_quota_limit.toLocaleString()} requests).
              Subsequent API calls will receive HTTP 429 until the quota resets on the 1st of next month at 00:00:00 UTC.
            </p>
          </div>
        </div>
      ) : isQuotaCritical ? (
        <div className="p-4 rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-200 text-xs flex items-start gap-3">
          <svg className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <div>
            <span className="font-semibold text-amber-300 block text-sm">Quota Alert: Approaching Monthly Limit</span>
            <p className="mt-1 text-amber-200/90 text-xs">
              You have consumed {quotaPercent}% of your monthly allowance ({summary?.monthly_quota_remaining.toLocaleString()} requests remaining).
            </p>
          </div>
        </div>
      ) : null}

      {/* Top Telemetry Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Monthly Quota Meter */}
        <div className="glass-card p-4 border border-surface-800 space-y-3">
          <div className="flex items-center justify-between text-xs text-surface-400">
            <span>Monthly Quota</span>
            <span className="font-mono text-white text-xs">{quotaPercent}%</span>
          </div>
          <div>
            <div className="text-xl font-bold text-white font-mono">
              {(summary?.requests_this_month ?? 0).toLocaleString()}
              <span className="text-xs text-surface-500 font-normal"> / {(summary?.monthly_quota_limit ?? 1000).toLocaleString()}</span>
            </div>
            <p className="text-[11px] text-surface-400 mt-0.5">
              {(summary?.monthly_quota_remaining ?? 0).toLocaleString()} requests remaining
            </p>
          </div>
          {/* Progress Bar */}
          <div className="w-full h-1.5 rounded-full bg-surface-950 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-500 ${
                isQuotaExhausted
                  ? 'bg-rose-500'
                  : isQuotaCritical
                  ? 'bg-amber-400'
                  : 'bg-emerald-400'
              }`}
              style={{ width: `${quotaPercent}%` }}
            />
          </div>
        </div>

        {/* Requests Today (UTC) */}
        <div className="glass-card p-4 border border-surface-800 space-y-2">
          <div className="flex items-center justify-between text-xs text-surface-400">
            <span>Requests Today (UTC)</span>
            <span className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {(summary?.requests_today ?? 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-surface-400">
            All-time: {(summary?.total_requests ?? 0).toLocaleString()} calls
          </p>
        </div>

        {/* Current Tier & Rate Limit */}
        <div className="glass-card p-4 border border-surface-800 space-y-2">
          <div className="flex items-center justify-between text-xs text-surface-400">
            <span>Active Tier</span>
            <span className="px-2 py-0.5 rounded-md bg-brand-500/15 border border-brand-500/30 text-brand-300 font-mono text-[10px] uppercase font-semibold">
              {summary?.primary_tier || 'development'}
            </span>
          </div>
          <div className="text-xl font-bold text-white font-mono">
            {summary?.rate_limit_rpm ?? 10} <span className="text-xs text-surface-400 font-normal">req / min</span>
          </div>
          <p className="text-[11px] text-surface-400">
            60s sliding window enforcement
          </p>
        </div>

        {/* Request Outcome Health */}
        <div className="glass-card p-4 border border-surface-800 space-y-2">
          <div className="flex items-center justify-between text-xs text-surface-400">
            <span>Execution Status</span>
            <span className="text-[10px] text-surface-400">Telemetry</span>
          </div>
          <div className="flex items-center gap-3 pt-1">
            <div className="text-center">
              <span className="block text-xs font-mono font-bold text-emerald-400">
                {summary?.successful_requests ?? 0}
              </span>
              <span className="text-[10px] text-surface-500">2xx OK</span>
            </div>
            <div className="w-px h-6 bg-surface-800" />
            <div className="text-center">
              <span className="block text-xs font-mono font-bold text-amber-400">
                {summary?.error_requests ?? 0}
              </span>
              <span className="text-[10px] text-surface-500">4xx/5xx</span>
            </div>
            <div className="w-px h-6 bg-surface-800" />
            <div className="text-center">
              <span className="block text-xs font-mono font-bold text-rose-400">
                {(summary?.rate_limited_requests ?? 0) + (summary?.quota_exceeded_requests ?? 0)}
              </span>
              <span className="text-[10px] text-surface-500">429 Blocked</span>
            </div>
          </div>
        </div>
      </div>

      {/* AI Copilot & Hybrid Inference Telemetry (Phase 4) */}
      <div className="glass-card p-5 border border-surface-800 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-white">AI Copilot & Hybrid Inference Telemetry</h3>
              <p className="text-xs text-surface-400">Natural language GIS analysis requests, quotas, and verified latency</p>
            </div>
          </div>
          <span className="px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono text-[10px] uppercase font-semibold">
            v2 Phase 4
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {/* AI Calls */}
          <div className="p-3.5 rounded-xl bg-surface-950/60 border border-surface-800/80 space-y-1">
            <span className="text-[11px] text-surface-400 block">AI Requests Executed</span>
            <div className="text-lg font-bold font-mono text-white">
              {(summary?.ai_usage?.total_requests ?? 0).toLocaleString()}
            </div>
            <p className="text-[10px] text-emerald-400">
              {(summary?.ai_usage?.successful_requests ?? 0).toLocaleString()} completed
            </p>
          </div>

          {/* AI Monthly Quota */}
          <div className="p-3.5 rounded-xl bg-surface-950/60 border border-surface-800/80 space-y-1">
            <span className="text-[11px] text-surface-400 block">AI Monthly Quota</span>
            <div className="text-lg font-bold font-mono text-white">
              {(summary?.ai_usage?.total_requests ?? 0).toLocaleString()}
              <span className="text-xs text-surface-500 font-normal"> / {(summary?.ai_usage?.monthly_quota_limit ?? 500).toLocaleString()}</span>
            </div>
            <p className="text-[10px] text-surface-400">
              Rate limit: {summary?.ai_usage?.rate_limit_rpm ?? 15} rpm
            </p>
          </div>

          {/* AI Average Latency */}
          <div className="p-3.5 rounded-xl bg-surface-950/60 border border-surface-800/80 space-y-1">
            <span className="text-[11px] text-surface-400 block">Avg Response Latency</span>
            <div className="text-lg font-bold font-mono text-cyan-400">
              {(summary?.ai_usage?.avg_duration_ms ?? 0) > 0 ? `${summary?.ai_usage?.avg_duration_ms} ms` : '—'}
            </div>
            <p className="text-[10px] text-surface-400">
              Fast-path &lt;50ms GIS engine
            </p>
          </div>

          {/* AI Blocked / Rate Limited */}
          <div className="p-3.5 rounded-xl bg-surface-950/60 border border-surface-800/80 space-y-1">
            <span className="text-[11px] text-surface-400 block">AI Rate Limits & Quotas</span>
            <div className="text-lg font-bold font-mono text-amber-400">
              {(summary?.ai_usage?.rate_limited_requests ?? 0) + (summary?.ai_usage?.quota_exceeded_requests ?? 0)}
            </div>
            <p className="text-[10px] text-surface-500">
              429 Throttled calls
            </p>
          </div>
        </div>

        <div className="px-3.5 py-2.5 rounded-xl bg-surface-900/40 border border-surface-800/60 flex items-center justify-between text-[11px] text-surface-400">
          <div className="flex items-center space-x-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>Usage reporting distinguishes provider-verified metrics from estimates. Token counts are never fabricated.</span>
          </div>
          <span className="text-surface-500 font-mono text-[10px]">Strict Bounds</span>
        </div>
      </div>

      {/* Daily Usage Chart (SVG) */}
      <div className="glass-card p-5 border border-surface-800 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold text-white">Daily Request Volume</h3>
            <p className="text-xs text-surface-400">Timestamped telemetry across past 14 days (UTC)</p>
          </div>
          {summary && summary.total_requests > 0 && (
            <span className="text-xs font-mono text-brand-300">
              Peak: {maxDailyCount} req/day
            </span>
          )}
        </div>

        {summary && summary.daily_usage && summary.daily_usage.some((d) => d.count > 0) ? (
          <div className="pt-2">
            <div className="flex items-end gap-1.5 h-36 px-2 pb-6 border-b border-surface-800 relative">
              {summary.daily_usage.map((point) => {
                const heightPercent = maxDailyCount > 0 ? Math.max(8, (point.count / maxDailyCount) * 100) : 0;
                return (
                  <div
                    key={point.date}
                    className="flex-1 flex flex-col items-center justify-end h-full group relative"
                  >
                    {/* Tooltip */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity absolute -top-8 px-2 py-1 bg-surface-950 border border-surface-700 text-white rounded text-[10px] font-mono whitespace-nowrap pointer-events-none z-10 shadow-lg">
                      {point.date}: <strong className="text-brand-300">{point.count} requests</strong>
                    </div>
                    {/* Bar */}
                    <div
                      style={{ height: `${heightPercent}%` }}
                      className={`w-full rounded-t transition-all ${
                        point.count > 0
                          ? 'bg-gradient-to-t from-brand-600 to-indigo-500 group-hover:from-brand-500 group-hover:to-indigo-400'
                          : 'bg-surface-800/40'
                      }`}
                    />
                    {/* Date label */}
                    <span className="absolute -bottom-5 text-[9px] font-mono text-surface-500 truncate w-full text-center">
                      {point.date.slice(5)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="p-10 text-center rounded-xl bg-surface-950/40 border border-dashed border-surface-800 space-y-2">
            <p className="text-xs text-surface-400">No request telemetry recorded yet for this period.</p>
            <p className="text-[11px] text-surface-500">
              Generate test requests via the API Playground to populate live daily charts and latency metrics.
            </p>
            {onNavigateToPlayground && (
              <button
                onClick={onNavigateToPlayground}
                className="mt-2 btn-secondary text-xs py-1.5 px-3 inline-flex items-center gap-1.5"
              >
                Open API Playground &rarr;
              </button>
            )}
          </div>
        )}
      </div>

      {/* Recent API Activity Table */}
      <div className="glass-card p-5 border border-surface-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-white">Recent API Activity</h3>
            <p className="text-xs text-surface-400">Latest recorded API requests and execution latency</p>
          </div>
          {keys.length > 1 && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-surface-400 text-[11px]">Filter Key:</span>
              <select
                value={selectedKeyFilter}
                onChange={(e) => setSelectedKeyFilter(e.target.value)}
                className="px-2.5 py-1 rounded-lg bg-surface-900 border border-surface-700 text-xs text-white focus:outline-none"
              >
                <option value="all">All Keys</option>
                {keys.map((k) => (
                  <option key={k.id} value={k.id}>
                    {k.name} ({k.prefix}...)
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {filteredActivity.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-800 text-surface-400 text-[11px]">
                  <th className="pb-2 font-medium">Timestamp (UTC)</th>
                  <th className="pb-2 font-medium">Method</th>
                  <th className="pb-2 font-medium">Endpoint</th>
                  <th className="pb-2 font-medium">Key</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60 font-mono text-[11px]">
                {filteredActivity.map((evt) => {
                  const isSuccess = evt.status_code >= 200 && evt.status_code < 300;
                  const isBlocked = evt.status_code === 429;
                  return (
                    <tr key={evt.id} className="hover:bg-surface-800/30 transition-colors">
                      <td className="py-2.5 text-surface-400">
                        {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </td>
                      <td className="py-2.5">
                        <span className="px-1.5 py-0.5 rounded bg-brand-500/20 text-brand-300 font-semibold text-[10px]">
                          {evt.method}
                        </span>
                      </td>
                      <td className="py-2.5 text-surface-300 truncate max-w-[200px]">
                        {evt.endpoint}
                      </td>
                      <td className="py-2.5 text-surface-400">
                        {evt.key_name ? `${evt.key_name} (${evt.key_prefix}...)` : evt.key_prefix}
                      </td>
                      <td className="py-2.5">
                        {isSuccess ? (
                          <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 font-sans font-medium text-[10px]">
                            {evt.status_code} OK
                          </span>
                        ) : isBlocked ? (
                          <span className="px-2 py-0.5 rounded-full bg-rose-500/15 border border-rose-500/30 text-rose-300 font-sans font-medium text-[10px]">
                            429 {evt.blocked_reason === 'quota' ? 'Quota Exceeded' : 'Throttled'}
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded-full bg-amber-500/15 border border-amber-500/30 text-amber-300 font-sans font-medium text-[10px]">
                            {evt.status_code} Error
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 text-surface-400">
                        {evt.duration_ms} ms
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-xs text-surface-500">
            No recent activity recorded for this selection.
          </div>
        )}
      </div>

      {/* Per-Key Usage Breakdown */}
      {keys.length > 0 && (
        <div className="glass-card p-5 border border-surface-800 space-y-4">
          <h3 className="text-sm font-semibold text-white">Per-Key Configuration & Quotas</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-800 text-surface-400 text-[11px]">
                  <th className="pb-2 font-medium">Key Name</th>
                  <th className="pb-2 font-medium">Prefix</th>
                  <th className="pb-2 font-medium">Tier</th>
                  <th className="pb-2 font-medium">Rate Limit</th>
                  <th className="pb-2 font-medium">Monthly Cap</th>
                  <th className="pb-2 font-medium">Lifetime Requests</th>
                  <th className="pb-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60 text-surface-300">
                {keys.map((k) => (
                  <tr key={k.id} className="hover:bg-surface-800/30 transition-colors">
                    <td className="py-2.5 font-medium text-white">{k.name}</td>
                    <td className="py-2.5 font-mono text-xs text-brand-300">{k.prefix}...</td>
                    <td className="py-2.5">
                      <span className="px-2 py-0.5 rounded-md bg-surface-800 border border-surface-700 text-surface-300 font-mono text-[10px] uppercase font-semibold">
                        {k.tier || 'development'}
                      </span>
                    </td>
                    <td className="py-2.5 font-mono text-xs">{k.rate_limit_rpm || 10} rpm</td>
                    <td className="py-2.5 font-mono text-xs">{(k.monthly_quota_limit || 1000).toLocaleString()}</td>
                    <td className="py-2.5 font-mono text-xs">{k.request_count.toLocaleString()}</td>
                    <td className="py-2.5">
                      {k.is_active ? (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-[10px] font-medium">
                          Active
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded-full bg-surface-800 border border-surface-700 text-surface-400 text-[10px] font-medium">
                          Revoked
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
