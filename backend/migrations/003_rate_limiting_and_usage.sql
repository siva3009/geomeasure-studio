-- ==============================================================================
-- GeoMeasure Studio v2 — Migration 003: Rate Limiting, Quotas and Usage Events
-- Target: Supabase PostgreSQL
-- Safe and Additive: Preserves existing api_keys table and all v1 data
-- ==============================================================================

-- 1. Add tier column to api_keys table if not already present
-- Existing keys safely default to 'development' tier
ALTER TABLE api_keys 
ADD COLUMN IF NOT EXISTS tier TEXT NOT NULL DEFAULT 'development';

-- 2. Create api_key_usage_events table for high-fidelity usage analytics
CREATE TABLE IF NOT EXISTS api_key_usage_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    api_key_id UUID NOT NULL REFERENCES api_keys(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    blocked_reason TEXT, -- NULL for permitted requests; 'rate_limit' or 'quota' when throttled
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 3. Create high-performance query indexes
-- Query recent events and sliding window by key
CREATE INDEX IF NOT EXISTS idx_usage_events_key_created ON api_key_usage_events(api_key_id, created_at DESC);

-- Query events by timestamp for retention cleanup and monthly aggregation
CREATE INDEX IF NOT EXISTS idx_usage_events_created ON api_key_usage_events(created_at);

-- Query events grouped by endpoint
CREATE INDEX IF NOT EXISTS idx_usage_events_endpoint ON api_key_usage_events(endpoint);

-- 4. Enable Row Level Security (RLS) on api_key_usage_events
ALTER TABLE api_key_usage_events ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view usage events only for API keys they own
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'api_key_usage_events' AND policyname = 'Users can view usage events for their own keys'
    ) THEN
        CREATE POLICY "Users can view usage events for their own keys"
            ON api_key_usage_events
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM api_keys 
                    WHERE api_keys.id = api_key_usage_events.api_key_id 
                      AND api_keys.user_id = auth.uid()
                )
            );
    END IF;
END
$$;
