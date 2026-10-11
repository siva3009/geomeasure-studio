-- ==============================================================================
-- GeoMeasure Studio v2 — Migration 002: Secure API Key Infrastructure
-- Target: Supabase PostgreSQL
-- Safe and Additive: Does not alter or drop any existing v1 tables or data
-- ==============================================================================

-- 1. Ensure pgcrypto extension is available for UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Create api_keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    prefix TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    request_count BIGINT NOT NULL DEFAULT 0
);

-- 3. Create performance indexes
-- Quick lookup by SHA-256 key hash during request authentication
CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);

-- Fast lookup of all keys owned by an authenticated user
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

-- Filter active keys by revocation and expiration
CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(user_id, revoked_at) WHERE revoked_at IS NULL;

-- 4. Enable Row Level Security (RLS) for least-privilege security
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- Policy: Authenticated users can view and manage only their own API keys
-- Made idempotent: Will not fail if executed multiple times in Supabase SQL Editor
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'api_keys' AND policyname = 'Users can view and manage their own API keys'
    ) THEN
        CREATE POLICY "Users can view and manage their own API keys"
            ON api_keys
            FOR ALL
            USING (auth.uid() = user_id)
            WITH CHECK (auth.uid() = user_id);
    END IF;
END
$$;

-- 5. Foreign key constraint: Associate user_id with Supabase auth.users if available
-- Safely checks if auth.users exists before adding the constraint (ensures compatibility with non-Supabase environments)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'auth' AND table_name = 'users'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_api_keys_user_id'
    ) THEN
        ALTER TABLE api_keys 
            ADD CONSTRAINT fk_api_keys_user_id 
            FOREIGN KEY (user_id) 
            REFERENCES auth.users(id) 
            ON DELETE CASCADE;
    END IF;
END
$$;

-- Note: FastAPI backend connects with database connection string (service/postgres role),
-- which bypasses RLS while enforcing strict user_id ownership in backend application logic.
-- Direct PostgREST or Supabase Client access adheres strictly to the RLS policy above.

