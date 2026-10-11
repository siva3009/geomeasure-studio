-- GeoMeasure Studio: Supabase PostgreSQL Schema
-- Execute in Supabase SQL Editor or let FastAPI auto-run on startup via init_db()

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS uploaded_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    source_crs TEXT,
    feature_count INTEGER,
    status TEXT NOT NULL DEFAULT 'processing',
    error_message TEXT,
    geojson JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS measurements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_id UUID NOT NULL REFERENCES uploaded_files(id) ON DELETE CASCADE,
    feature_index INTEGER NOT NULL,
    feature_id TEXT,
    geometry_type TEXT NOT NULL,
    geometry_wkt TEXT,
    source_crs TEXT,
    measurement_crs TEXT,
    area_sq_meters DOUBLE PRECISION,
    length_meters DOUBLE PRECISION,
    measurement_unit TEXT DEFAULT 'meters',
    properties JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_measurements_file_id ON measurements(file_id);
CREATE INDEX IF NOT EXISTS idx_uploaded_files_created_at ON uploaded_files(created_at DESC);

-- v2 Phase 1: API Keys
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

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

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


