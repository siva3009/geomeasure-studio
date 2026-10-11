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
