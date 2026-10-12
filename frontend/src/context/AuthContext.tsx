import React, { createContext, useEffect, useState, useCallback } from 'react';
import type { User, Session } from '@supabase/supabase-js';
import { supabase, isSupabaseConfigured } from '../lib/supabase';

interface AuthContextType {
  user: User | null;
  session: Session | null;
  loading: boolean;
  isConfigured: boolean;
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>;
  signUp: (email: string, password: string) => Promise<{ error: Error | null; user: User | null }>;
  signOut: () => Promise<void>;
  getAccessToken: () => Promise<string | null>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  session: null,
  loading: true,
  isConfigured: false,
  signIn: async () => ({ error: new Error('Supabase not configured') }),
  signUp: async () => ({ error: new Error('Supabase not configured'), user: null }),
  signOut: async () => {},
  getAccessToken: async () => null,
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const configured = isSupabaseConfigured();
  const [loading, setLoading] = useState<boolean>(configured);

  useEffect(() => {
    if (!configured || !supabase) {
      return;
    }


    // Check active session
    supabase.auth.getSession().then(({ data: { session: activeSession } }) => {
      setSession(activeSession);
      setUser(activeSession?.user ?? null);
      setLoading(false);
    });

    // Listen for auth state changes (login, logout, refresh)
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, currentSession) => {
      setSession(currentSession);
      setUser(currentSession?.user ?? null);
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [configured]);

  const signIn = useCallback(async (email: string, password: string) => {
    if (!configured || !supabase) {
      return { error: new Error('Supabase authentication is not configured in this environment.') };
    }
    const { error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    return { error: error ? new Error(error.message) : null };
  }, [configured]);

  const signUp = useCallback(async (email: string, password: string) => {
    if (!configured || !supabase) {
      return { error: new Error('Supabase authentication is not configured in this environment.'), user: null };
    }
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
    });
    return { error: error ? new Error(error.message) : null, user: data?.user ?? null };
  }, [configured]);

  const signOut = useCallback(async () => {
    if (configured && supabase) {
      await supabase.auth.signOut();
    }
    setUser(null);
    setSession(null);
  }, [configured]);

  const getAccessToken = useCallback(async (): Promise<string | null> => {
    if (!configured || !supabase) {
      return null;
    }
    const { data: { session: currentSession } } = await supabase.auth.getSession();
    return currentSession?.access_token ?? null;
  }, [configured]);

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        loading,
        isConfigured: configured,
        signIn,
        signUp,
        signOut,
        getAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export { AuthContext };
export { useAuth } from './useAuth';




