-- ══════════════════════════════════════════════════════════════
-- SentinelOS — PostgreSQL Initialization
--
-- This script runs once when the PostgreSQL container is first
-- created. It sets up extensions and baseline configuration.
--
-- The actual schema (tables, indexes) is managed by Alembic
-- migrations — not here. This file only bootstraps extensions
-- that must exist before the application runs.
-- ══════════════════════════════════════════════════════════════

-- Enable UUID generation (used for primary keys)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pg_trgm for fast text search on event payloads (future use)
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Set timezone to UTC for all connections
ALTER DATABASE sentinelos SET timezone TO 'UTC';

-- Confirm
SELECT 'SentinelOS PostgreSQL initialized successfully' AS status;
