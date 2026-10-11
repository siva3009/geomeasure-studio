/* ======================================================
   GeoMeasure Studio — Developer Portal Container
   Hosts Overview, API Keys, Playground & Documentation Tabs
   ====================================================== */

import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../../context/useAuth';

import type { ApiKeyMetadata, CreateApiKeyResponse, UsageSummary } from '../../types';
import { listApiKeys, createApiKey, revokeApiKey, getUsageSummary } from '../../api/client';
import { OverviewTab } from './OverviewTab';
import { ApiKeysTab } from './ApiKeysTab';
import { UsageTab } from './UsageTab';
import { PlaygroundTab } from './PlaygroundTab';
import { DocsTab } from './DocsTab';
import { AuthModal } from './AuthModal';

export const DeveloperPortal: React.FC = () => {
  const { user, loading: authLoading, isConfigured, getAccessToken, signOut } = useAuth();
  const [activeTab, setActiveTab] = useState<'overview' | 'keys' | 'usage' | 'playground' | 'docs'>('overview');
  const [showAuthModal, setShowAuthModal] = useState(false);

  // API keys state
  const [keys, setKeys] = useState<ApiKeyMetadata[]>([]);
  const [keysLoading, setKeysLoading] = useState(false);
  const [keysError, setKeysError] = useState<string | null>(null);

  // Usage summary state
  const [usageSummary, setUsageSummary] = useState<UsageSummary | null>(null);
  const [usageLoading, setUsageLoading] = useState(false);

  // Fetch keys and usage summary whenever user is authenticated
  const loadData = useCallback(async () => {
    if (!user) {
      setKeys([]);
      setUsageSummary(null);
      return;
    }
    setKeysLoading(true);
    setUsageLoading(true);
    setKeysError(null);
    try {
      const token = await getAccessToken();
      if (!token) {
        throw new Error('No active authentication token found.');
      }
      const [keysData, usageData] = await Promise.all([
        listApiKeys(token),
        getUsageSummary(token).catch((err) => {
          console.warn('Failed to fetch usage summary:', err);
          return null;
        }),
      ]);
      setKeys(keysData);
      if (usageData) setUsageSummary(usageData);
    } catch (err: unknown) {
      console.error('Failed to load developer data:', err);
      setKeysError(err instanceof Error ? err.message : 'Failed to fetch developer data.');
    } finally {
      setKeysLoading(false);
      setUsageLoading(false);
    }
  }, [user, getAccessToken]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateKey = async (name: string, expiresInDays: number | null, tier?: string): Promise<CreateApiKeyResponse> => {
    const token = await getAccessToken();
    if (!token) throw new Error('Authentication required.');
    const res = await createApiKey({ name, expires_in_days: expiresInDays, tier }, token);
    await loadData();
    return res;
  };

  const handleRevokeKey = async (keyId: string): Promise<void> => {
    const token = await getAccessToken();
    if (!token) throw new Error('Authentication required.');
    await revokeApiKey(keyId, token);
    await loadData();
  };

  return (
    <div className="space-y-6">
      {/* Developer Sub-Header Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-surface-800/80">
        <div className="flex items-center gap-1.5 p-1 bg-surface-900/90 rounded-xl border border-surface-800 w-fit">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-2 px-3.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'overview'
                ? 'bg-brand-600 text-white shadow-sm shadow-brand-600/30 font-semibold'
                : 'text-surface-400 hover:text-surface-200'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('keys')}
            className={`py-2 px-3.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'keys'
                ? 'bg-brand-600 text-white shadow-sm shadow-brand-600/30 font-semibold'
                : 'text-surface-400 hover:text-surface-200'
            }`}
          >
            API Credentials
          </button>
          <button
            onClick={() => setActiveTab('usage')}
            className={`py-2 px-3.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'usage'
                ? 'bg-brand-600 text-white shadow-sm shadow-brand-600/30 font-semibold'
                : 'text-surface-400 hover:text-surface-200'
            }`}
          >
            Usage & Limits
          </button>
          <button
            onClick={() => setActiveTab('playground')}
            className={`py-2 px-3.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'playground'
                ? 'bg-brand-600 text-white shadow-sm shadow-brand-600/30 font-semibold'
                : 'text-surface-400 hover:text-surface-200'
            }`}
          >
            API Playground
          </button>
          <button
            onClick={() => setActiveTab('docs')}
            className={`py-2 px-3.5 rounded-lg text-xs font-medium transition-all ${
              activeTab === 'docs'
                ? 'bg-brand-600 text-white shadow-sm shadow-brand-600/30 font-semibold'
                : 'text-surface-400 hover:text-surface-200'
            }`}
          >
            Documentation
          </button>
        </div>

        {/* User Status / Auth Badge */}
        <div className="flex items-center gap-3">
          {authLoading ? (
            <div className="w-5 h-5 border-2 border-brand-400 border-t-transparent rounded-full animate-spin" />
          ) : user ? (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-surface-900 border border-surface-700/60 text-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-400" />
                <span className="text-surface-300 font-mono text-[11px] truncate max-w-[200px]">
                  {user.email || 'Authenticated User'}
                </span>
              </div>
              <button
                onClick={() => signOut()}
                className="btn-ghost text-xs py-1.5 px-3 text-surface-400 hover:text-rose-400 hover:bg-rose-500/10"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="btn-primary text-xs py-2 px-4 shadow-md shadow-brand-600/25 flex items-center gap-1.5"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
              </svg>
              <span>Sign In / Register</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Tab Content */}
      {keysError && (
        <div className="p-3.5 rounded-xl bg-rose-500/15 border border-rose-500/30 text-rose-200 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-rose-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{keysError}</span>
          </div>
          <button onClick={loadData} className="underline text-rose-300 font-medium">Retry</button>
        </div>
      )}

      {/* If user is not authenticated and is on Overview, Keys, or Usage, show the Authenticated Prompt Card */}
      {!user && (activeTab === 'overview' || activeTab === 'keys' || activeTab === 'usage') ? (
        <div className="glass-card p-10 border border-surface-700/50 text-center max-w-xl mx-auto space-y-4 my-8">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-brand-500 to-indigo-600 mx-auto flex items-center justify-center text-white shadow-xl shadow-brand-500/30">
            <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Developer Authentication Required</h3>
            <p className="text-xs text-surface-400 mt-1 max-w-md mx-auto">
              Sign in with your developer account to generate cryptographically random API keys, inspect usage counters, and manage credentials.
            </p>
          </div>
          <div className="pt-2 flex justify-center gap-3">
            <button
              onClick={() => setShowAuthModal(true)}
              className="btn-primary text-xs py-2.5 px-6 shadow-lg shadow-brand-600/30"
            >
              Sign In with Supabase Auth
            </button>
            <button
              onClick={() => setActiveTab('docs')}
              className="btn-secondary text-xs py-2.5 px-4"
            >
              Read Documentation
            </button>
          </div>
          <div className="text-[11px] text-surface-500 pt-2">
            {!isConfigured && (
              <span className="text-amber-400 block">
                Note: Configure VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in frontend/.env to enable live sign-in.
              </span>
            )}
          </div>
        </div>
      ) : activeTab === 'overview' ? (
        <OverviewTab
          keys={keys}
          usageSummary={usageSummary}
          loading={keysLoading || usageLoading}
          onCreateKeyClick={() => {
            if (!user) setShowAuthModal(true);
            else setActiveTab('keys');
          }}
          onNavigateToPlayground={() => setActiveTab('playground')}
          onNavigateToDocs={() => setActiveTab('docs')}
          onNavigateToUsage={() => setActiveTab('usage')}
        />
      ) : activeTab === 'keys' ? (
        <ApiKeysTab
          keys={keys}
          loading={keysLoading}
          onRefresh={loadData}
          onCreateKey={handleCreateKey}
          onRevokeKey={handleRevokeKey}
        />
      ) : activeTab === 'usage' ? (
        <UsageTab
          summary={usageSummary}
          keys={keys}
          loading={usageLoading}
          onRefresh={loadData}
          onNavigateToPlayground={() => setActiveTab('playground')}
        />
      ) : activeTab === 'playground' ? (
        <PlaygroundTab keys={keys} />
      ) : (
        <DocsTab />
      )}

      {/* Auth Modal */}
      <AuthModal
        isOpen={showAuthModal}
        onClose={() => {
          setShowAuthModal(false);
          loadData();
        }}
      />
    </div>
  );
};
