/* ======================================================
   GeoMeasure Studio — API Key Management Tab
   Creation, Listing, One-Time Plaintext Modal, Details & Revocation
   ====================================================== */

import React, { useState } from 'react';
import type { ApiKeyMetadata, CreateApiKeyResponse } from '../../types';

interface ApiKeysTabProps {
  keys: ApiKeyMetadata[];
  loading: boolean;
  onRefresh: () => void;
  onCreateKey: (name: string, expiresInDays: number | null, tier?: string) => Promise<CreateApiKeyResponse>;
  onRevokeKey: (keyId: string) => Promise<void>;
}

export const ApiKeysTab: React.FC<ApiKeysTabProps> = ({
  keys,
  loading,
  onRefresh,
  onCreateKey,
  onRevokeKey,
}) => {
  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [newKeyExpiration, setNewKeyExpiration] = useState<string>('none');
  const [newKeyTier, setNewKeyTier] = useState<string>('development');
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // One-time newly generated secret modal
  const [createdSecretData, setCreatedSecretData] = useState<CreateApiKeyResponse | null>(null);
  const [copiedSecret, setCopiedSecret] = useState(false);
  const [revealSecret, setRevealSecret] = useState(true);

  // Key inspection modal
  const [inspectedKey, setInspectedKey] = useState<ApiKeyMetadata | null>(null);

  // Revocation confirmation modal
  const [keyToRevoke, setKeyToRevoke] = useState<ApiKeyMetadata | null>(null);
  const [revokeSubmitting, setRevokeSubmitting] = useState(false);

  // Search filter
  const [searchQuery, setSearchQuery] = useState('');

  const filteredKeys = keys.filter(
    (k) =>
      k.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      k.prefix.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    setCreateSubmitting(true);
    setCreateError(null);
    try {
      const expDays = newKeyExpiration === 'none' ? null : parseInt(newKeyExpiration, 10);
      const res = await onCreateKey(newKeyName.trim(), expDays, newKeyTier);
      setShowCreateModal(false);
      setNewKeyName('');
      setNewKeyExpiration('none');
      setNewKeyTier('development');
      setCreatedSecretData(res);
      setCopiedSecret(false);
      onRefresh();
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : 'Failed to generate API key.');
    } finally {
      setCreateSubmitting(false);
    }
  };

  const handleCopySecret = async () => {
    if (!createdSecretData) return;
    try {
      await navigator.clipboard.writeText(createdSecretData.api_key);
      setCopiedSecret(true);
      setTimeout(() => setCopiedSecret(false), 3000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const handleConfirmRevoke = async () => {
    if (!keyToRevoke) return;
    setRevokeSubmitting(true);
    try {
      await onRevokeKey(keyToRevoke.id);
      setKeyToRevoke(null);
      onRefresh();
    } catch (err) {
      console.error('Revocation failed:', err);
    } finally {
      setRevokeSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Action Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-white">API Credentials</h2>
          <p className="text-xs text-surface-400">
            Create, inspect, and revoke API keys for programmatic access to GeoMeasure endpoints.
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="btn-secondary text-xs py-2 px-3 flex items-center gap-1.5"
            title="Refresh keys list"
          >
            <svg className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
          <button
            onClick={() => { setShowCreateModal(true); setCreateError(null); }}
            className="btn-primary text-xs py-2 px-4 flex items-center gap-2 shadow-lg shadow-brand-600/25"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
            </svg>
            Create API Key
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative">
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Filter by key name or prefix (e.g. gm_live_...)"
          className="w-full px-4 py-2.5 pl-10 rounded-xl bg-surface-900/80 border border-surface-700/50 text-white text-xs placeholder:text-surface-500 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
        />
        <svg className="w-4 h-4 text-surface-500 absolute left-3.5 top-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
      </div>

      {/* Keys Table Card */}
      <div className="glass-card border border-surface-700/40 overflow-hidden">
        {loading && keys.length === 0 ? (
          <div className="py-16 text-center text-surface-500 text-xs flex items-center justify-center gap-3">
            <div className="w-5 h-5 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
            <span>Fetching API credentials...</span>
          </div>
        ) : filteredKeys.length === 0 ? (
          <div className="py-16 text-center text-surface-500 text-xs space-y-3">
            <div className="w-12 h-12 rounded-2xl bg-surface-800/80 mx-auto flex items-center justify-center text-surface-400">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-surface-300">
              {searchQuery ? 'No matching keys found.' : 'No API keys created yet.'}
            </p>
            <p className="text-surface-500 max-w-sm mx-auto">
              API keys allow automated GIS scripts, pipelines, and server applications to interact with GeoMeasure Studio.
            </p>
            {!searchQuery && (
              <button
                onClick={() => setShowCreateModal(true)}
                className="btn-primary text-xs py-2 px-4 inline-flex items-center gap-1.5 mt-2"
              >
                Create First Key
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-surface-800 bg-surface-950/40 text-surface-400 uppercase text-[10px] tracking-wider">
                  <th className="py-3 px-5 font-semibold">Name</th>
                  <th className="py-3 px-4 font-semibold">Prefix</th>
                  <th className="py-3 px-4 font-semibold">Tier</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Requests</th>
                  <th className="py-3 px-4 font-semibold">Created</th>
                  <th className="py-3 px-4 font-semibold">Last Used</th>
                  <th className="py-3 px-4 font-semibold">Expires</th>
                  <th className="py-3 px-5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-800/60">
                {filteredKeys.map((k) => (
                  <tr key={k.id} className="hover:bg-surface-800/20 transition-colors">
                    <td className="py-3.5 px-5 font-medium text-white">
                      <div className="flex items-center gap-2">
                        <span>{k.name}</span>
                      </div>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-surface-300 text-[11px]">
                      <span className="px-2 py-0.5 rounded bg-surface-950 border border-surface-800">
                        {k.prefix}...
                      </span>
                    </td>
                    <td className="py-3.5 px-4 font-mono text-[11px]">
                      <span className="px-2 py-0.5 rounded bg-surface-950 border border-surface-800 text-surface-300 uppercase text-[10px] font-semibold">
                        {k.tier || 'development'}
                      </span>
                      <span className="text-[10px] text-surface-500 block mt-0.5 font-sans">
                        {k.rate_limit_rpm || 10} rpm
                      </span>
                    </td>
                    <td className="py-3.5 px-4">
                      {k.is_active ? (
                        <span className="badge-completed">Active</span>
                      ) : k.revoked_at ? (
                        <span className="badge-error">Revoked</span>
                      ) : (
                        <span className="badge-processing">Expired</span>
                      )}
                    </td>
                    <td className="py-3.5 px-4 font-mono text-surface-300">
                      {(k.request_count || 0).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-surface-400 text-[11px]">
                      {new Date(k.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-3.5 px-4 text-surface-400 text-[11px]">
                      {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="py-3.5 px-4 text-surface-400 text-[11px]">
                      {k.expires_at ? new Date(k.expires_at).toLocaleDateString() : 'Never'}
                    </td>
                    <td className="py-3.5 px-5 text-right space-x-2">
                      <button
                        onClick={() => setInspectedKey(k)}
                        className="btn-ghost text-[11px] py-1 px-2.5 text-surface-300 hover:text-white"
                        title="View key metadata"
                      >
                        Details
                      </button>
                      {k.is_active && (
                        <button
                          onClick={() => setKeyToRevoke(k)}
                          className="btn-ghost text-[11px] py-1 px-2.5 text-rose-400 hover:text-rose-300 hover:bg-rose-500/10"
                          title="Revoke key immediately"
                        >
                          Revoke
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ======================================================
          1. Create Key Modal
          ====================================================== */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="glass-card max-w-md w-full p-6 border border-surface-700/60 shadow-2xl bg-surface-900/95">
            <div className="flex items-center justify-between pb-4 border-b border-surface-800/80 mb-5">
              <h3 className="text-base font-semibold text-white">Generate New API Key</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-surface-400 hover:text-surface-200 p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            {createError && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-200 text-xs">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-surface-300 mb-1.5">
                  Key Name / Description
                </label>
                <input
                  type="text"
                  required
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="e.g. Production GIS Pipeline"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-950 border border-surface-700/60 text-white text-xs placeholder:text-surface-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                />
                <p className="text-[11px] text-surface-500 mt-1">
                  A descriptive name to identify which system or client will use this credential.
                </p>
              </div>

              <div>
                <label className="block text-xs font-medium text-surface-300 mb-1.5">
                  Expiration
                </label>
                <select
                  value={newKeyExpiration}
                  onChange={(e) => setNewKeyExpiration(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-950 border border-surface-700/60 text-white text-xs focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                >
                  <option value="none">Never expires (Recommended for servers)</option>
                  <option value="30">30 days</option>
                  <option value="60">60 days</option>
                  <option value="90">90 days</option>
                  <option value="365">1 year (365 days)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-surface-300 mb-1.5">
                  Service Tier & Allowance
                </label>
                <select
                  value={newKeyTier}
                  onChange={(e) => setNewKeyTier(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-950 border border-surface-700/60 text-white text-xs focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
                >
                  <option value="development">Development — 10 req/min · 1,000 req/month</option>
                  <option value="standard">Standard — 60 req/min · 25,000 req/month</option>
                  <option value="higher-volume">Higher-volume — 120 req/min · 100,000 req/month</option>
                </select>
                <p className="text-[11px] text-surface-500 mt-1">
                  Enforces sliding-window rate limiting and monthly request quota.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-surface-950 border border-surface-800 text-[11px] text-surface-400">
                <span className="font-semibold text-surface-300">Security Notice:</span> The complete plaintext API key will only be shown once immediately after creation.
              </div>

              <div className="flex items-center justify-end gap-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="btn-secondary text-xs py-2 px-4"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createSubmitting}
                  className="btn-primary text-xs py-2 px-5 flex items-center gap-2"
                >
                  {createSubmitting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Generating...</span>
                    </>
                  ) : (
                    <span>Generate Key</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================
          2. One-Time Secret Display Modal (CRITICAL)
          ====================================================== */}
      {createdSecretData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fade-in">
          <div className="glass-card max-w-lg w-full p-6 border border-emerald-500/40 shadow-2xl bg-surface-900/98 space-y-5">
            <div className="flex items-center gap-3 text-emerald-400">
              <div className="w-10 h-10 rounded-xl bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center shrink-0">
                <svg className="w-5 h-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">API Key Successfully Created</h3>
                <p className="text-xs text-emerald-400/80">Copy your key now — it will never be displayed again</p>
              </div>
            </div>

            {/* Warning Alert */}
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-start gap-2.5">
              <svg className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div className="space-y-1">
                <p className="font-semibold text-amber-300">Store this secret securely</p>
                <p className="text-[11px] text-amber-200/90 leading-relaxed">
                  For your security, we store only a SHA-256 cryptographic hash of this key. If you lose this key, you must revoke it and generate a replacement.
                </p>
              </div>
            </div>

            {/* Secret Display Box */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-surface-400">
                <span className="font-medium text-surface-300">{createdSecretData.name}</span>
                <button
                  onClick={() => setRevealSecret(!revealSecret)}
                  className="text-[11px] text-brand-400 hover:text-brand-300 transition"
                >
                  {revealSecret ? 'Mask Secret' : 'Reveal Secret'}
                </button>
              </div>

              <div className="flex items-center gap-2 p-3 rounded-xl bg-surface-950 border border-surface-700 font-mono text-xs text-white overflow-hidden">
                <span className="truncate flex-1 select-all font-semibold">
                  {revealSecret
                    ? createdSecretData.api_key
                    : createdSecretData.api_key.slice(0, 12) + '••••••••••••••••••••••••••••••••'}
                </span>
                <button
                  onClick={handleCopySecret}
                  className="px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 text-white text-xs font-sans font-medium flex items-center gap-1.5 shrink-0 transition shadow-sm"
                >
                  {copiedSecret ? (
                    <>
                      <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span>Copied!</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3" />
                      </svg>
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={() => setCreatedSecretData(null)}
                className="w-full py-2.5 btn-primary text-xs font-semibold shadow-lg shadow-brand-600/30"
              >
                I have saved my API key securely
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================
          3. Key Details Inspection Modal
          ====================================================== */}
      {inspectedKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
          <div className="glass-card max-w-md w-full p-6 border border-surface-700/60 shadow-2xl bg-surface-900/95 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-surface-800">
              <h3 className="text-base font-semibold text-white">API Key Metadata</h3>
              <button
                onClick={() => setInspectedKey(null)}
                className="text-surface-400 hover:text-surface-200 p-1"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-surface-500 block text-[11px]">Key Name</span>
                <span className="font-semibold text-white text-sm">{inspectedKey.name}</span>
              </div>
              <div>
                <span className="text-surface-500 block text-[11px]">Display Prefix</span>
                <span className="font-mono text-brand-300">{inspectedKey.prefix}...</span>
              </div>
              <div>
                <span className="text-surface-500 block text-[11px]">Key ID (UUID)</span>
                <span className="font-mono text-surface-300 text-[11px] select-all">{inspectedKey.id}</span>
              </div>
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <span className="text-surface-500 block text-[11px]">Tier Plan</span>
                  <span className="font-semibold text-white capitalize">{inspectedKey.tier || 'development'}</span>
                </div>
                <div>
                  <span className="text-surface-500 block text-[11px]">Rate Limit</span>
                  <span className="font-mono text-surface-300">{inspectedKey.rate_limit_rpm || 10} req/min</span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div>
                  <span className="text-surface-500 block text-[11px]">Total Calls</span>
                  <span className="font-mono font-semibold text-white">{(inspectedKey.request_count || 0).toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-surface-500 block text-[11px]">Status</span>
                  <span className={inspectedKey.is_active ? 'text-emerald-400 font-semibold' : 'text-rose-400 font-semibold'}>
                    {inspectedKey.is_active ? 'Active' : inspectedKey.revoked_at ? 'Revoked' : 'Expired'}
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <span className="text-surface-500 block text-[11px]">Created At</span>
                  <span className="text-surface-300">{new Date(inspectedKey.created_at).toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-surface-500 block text-[11px]">Last Used</span>
                  <span className="text-surface-300">
                    {inspectedKey.last_used_at ? new Date(inspectedKey.last_used_at).toLocaleString() : 'Never'}
                  </span>
                </div>
              </div>
              {inspectedKey.revoked_at && (
                <div>
                  <span className="text-rose-400 block text-[11px]">Revoked At</span>
                  <span className="text-rose-300">{new Date(inspectedKey.revoked_at).toLocaleString()}</span>
                </div>
              )}
            </div>

            <div className="p-3 rounded-xl bg-surface-950 border border-surface-800 text-[11px] text-surface-400 leading-relaxed">
              <span className="font-semibold text-surface-300">Security Architecture:</span> The plaintext secret is never stored on the server or retrievable after initial creation. Stored key hash is kept in an internal indexed column and never transmitted.
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setInspectedKey(null)}
                className="btn-secondary text-xs py-2 px-4"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================
          4. Revocation Confirmation Modal
          ====================================================== */}
      {keyToRevoke && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
          <div className="glass-card max-w-md w-full p-6 border border-rose-500/40 shadow-2xl bg-surface-900/98 space-y-4">
            <div className="flex items-center gap-3 text-rose-400">
              <div className="w-10 h-10 rounded-xl bg-rose-500/20 border border-rose-500/30 flex items-center justify-center shrink-0">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </div>
              <div>
                <h3 className="text-base font-semibold text-white">Revoke API Key</h3>
                <p className="text-xs text-rose-400/80">Immediate revocation</p>
              </div>
            </div>

            <p className="text-xs text-surface-300 leading-relaxed">
              Are you sure you want to revoke key <strong className="text-white">"{keyToRevoke.name}"</strong> (<span className="font-mono text-surface-400">{keyToRevoke.prefix}...</span>)?
            </p>

            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/25 text-rose-200 text-xs">
              <strong>Warning:</strong> Any application or pipeline using this key will immediately receive HTTP 401 Unauthorized errors. This action cannot be undone.
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={() => setKeyToRevoke(null)}
                className="btn-secondary text-xs py-2 px-4"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={revokeSubmitting}
                onClick={handleConfirmRevoke}
                className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-xl font-medium text-xs transition shadow-lg shadow-rose-600/30 flex items-center gap-1.5"
              >
                {revokeSubmitting ? 'Revoking...' : 'Yes, Revoke Key'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
