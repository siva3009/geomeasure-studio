"""
Database connection management and table initialization.
Uses psycopg2 for synchronous PostgreSQL access to Supabase.
"""

import psycopg2
import psycopg2.extras
import logging
from contextlib import contextmanager
from app.config import settings

logger = logging.getLogger(__name__)

# Register UUID adapter for psycopg2
psycopg2.extras.register_uuid()

# SQL for creating tables
CREATE_TABLES_SQL = """
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

CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name TEXT NOT NULL,
    key_hash TEXT NOT NULL UNIQUE,
    prefix TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'development',
    created_at TIMESTAMPTZ DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    request_count BIGINT NOT NULL DEFAULT 0
);

ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'development';

CREATE UNIQUE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);

CREATE TABLE IF NOT EXISTS api_key_usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    blocked_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_usage_events_key_created ON api_key_usage_events(api_key_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON api_key_usage_events(created_at);
CREATE INDEX IF NOT EXISTS idx_usage_events_endpoint ON api_key_usage_events(endpoint);
"""


def get_connection():
    """Create a new database connection."""
    try:
        conn = psycopg2.connect(
            settings.database_url,
            connect_timeout=settings.db_connect_timeout,
        )
        return conn
    except psycopg2.Error as e:
        logger.error(f"Database connection failed: {e}")
        raise


@contextmanager
def get_db():
    """Context manager for database connections with auto-commit/rollback."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database tables. Called on application startup."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute(CREATE_TABLES_SQL)
        logger.info("Database tables initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def check_db_connection() -> bool:
    """Check if the database is reachable. Used by health endpoint."""
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
    except Exception:
        return False
