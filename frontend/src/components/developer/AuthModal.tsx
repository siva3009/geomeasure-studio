/* ======================================================
   GeoMeasure Studio — Developer Auth Modal
   Supabase Authentication (Sign In & Sign Up)
   ====================================================== */

import React, { useState } from 'react';
import { useAuth } from '../../context/useAuth';


interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultMode?: 'signin' | 'signup';
}

export const AuthModal: React.FC<AuthModalProps> = ({
  isOpen,
  onClose,
  defaultMode = 'signin',
}) => {
  const { signIn, signUp, isConfigured } = useAuth();
  const [mode, setMode] = useState<'signin' | 'signup'>(defaultMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    if (!email.trim() || !password.trim()) {
      setErrorMsg('Please enter both email and password.');
      return;
    }

    if (password.length < 6) {
      setErrorMsg('Password must be at least 6 characters long.');
      return;
    }

    setLoading(true);
    try {
      if (mode === 'signin') {
        const { error } = await signIn(email, password);
        if (error) {
          setErrorMsg(error.message);
        } else {
          onClose();
        }
      } else {
        const { error, user } = await signUp(email, password);
        if (error) {
          setErrorMsg(error.message);
        } else if (user && !user.confirmed_at) {
          setSuccessMsg('Account created! Please check your email inbox to confirm your registration, or sign in.');
          setMode('signin');
        } else {
          setSuccessMsg('Account created successfully!');
          onClose();
        }
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Authentication failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fade-in">
      <div className="glass-card max-w-md w-full p-6 border border-surface-700/60 shadow-2xl shadow-surface-950/80 bg-surface-900/95">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-surface-800/80 mb-5">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-500 to-indigo-600 flex items-center justify-center shadow-md shadow-brand-500/20">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
              </svg>
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Developer Authentication</h3>
              <p className="text-xs text-surface-400">Supabase Auth Session</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-surface-400 hover:text-surface-200 p-1.5 rounded-lg hover:bg-surface-800 transition"
            aria-label="Close modal"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* If Supabase is unconfigured, display guide */}
        {!isConfigured ? (
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/25 text-amber-200 text-xs space-y-2">
            <div className="flex items-center gap-2 font-semibold text-amber-300">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>Supabase Environment Configuration Required</span>
            </div>
            <p>
              To authenticate developers and manage API keys, configure your Supabase public credentials in <code className="px-1.5 py-0.5 bg-surface-950 rounded text-amber-100">frontend/.env</code>:
            </p>
            <pre className="p-2.5 bg-surface-950/80 rounded font-mono text-[11px] text-surface-300 overflow-x-auto">
{`VITE_SUPABASE_URL=https://[YOUR-PROJECT].supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...`}
            </pre>
            <p className="text-[11px] text-surface-400">
              Obtain these from your Supabase Dashboard &rarr; Project Settings &rarr; API.
            </p>
          </div>
        ) : (
          <>
            {/* Tabs */}
            <div className="flex p-1 bg-surface-950/80 rounded-xl border border-surface-800 mb-5">
              <button
                type="button"
                onClick={() => { setMode('signin'); setErrorMsg(null); }}
                className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all ${
                  mode === 'signin'
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => { setMode('signup'); setErrorMsg(null); }}
                className={`flex-1 py-1.5 text-xs font-medium rounded-lg transition-all ${
                  mode === 'signup'
                    ? 'bg-brand-600 text-white shadow-sm'
                    : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                Create Account
              </button>
            </div>

            {/* Notifications */}
            {errorMsg && (
              <div className="mb-4 p-3 rounded-xl bg-red-500/15 border border-red-500/30 text-red-200 text-xs flex items-start gap-2">
                <svg className="w-4 h-4 text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{errorMsg}</span>
              </div>
            )}
            {successMsg && (
              <div className="mb-4 p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-200 text-xs flex items-start gap-2">
                <svg className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
                <span>{successMsg}</span>
              </div>
            )}

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-surface-300 mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="developer@company.com"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-950 border border-surface-700/60 text-white text-xs placeholder:text-surface-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-surface-300 mb-1.5">
                  Password
                </label>
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-surface-950 border border-surface-700/60 text-white text-xs placeholder:text-surface-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 btn-primary text-xs flex items-center justify-center gap-2 mt-2"
              >
                {loading ? (
                  <>
                    <div className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    <span>Processing...</span>
                  </>
                ) : mode === 'signin' ? (
                  <span>Sign In to Dashboard</span>
                ) : (
                  <span>Create Developer Account</span>
                )}
              </button>
            </form>
          </>
        )}

        <div className="mt-5 text-center text-[11px] text-surface-500 border-t border-surface-800/60 pt-4">
          Secured with Supabase Authentication. JWT tokens verify ownership on all key management calls.
        </div>
      </div>
    </div>
  );
};
