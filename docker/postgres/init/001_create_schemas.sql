-- Runs only when the PostgreSQL data directory is initialized for the first time.
BEGIN;

CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS intermediate;
CREATE SCHEMA IF NOT EXISTS gold;
CREATE SCHEMA IF NOT EXISTS marts;
CREATE SCHEMA IF NOT EXISTS audit;

CREATE TABLE IF NOT EXISTS audit.bootstrap_info (
    bootstrap_id SMALLINT PRIMARY KEY CHECK (bootstrap_id = 1),
    schema_version INTEGER NOT NULL,
    initialized_at_utc TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO audit.bootstrap_info (bootstrap_id, schema_version)
VALUES (1, 1)
ON CONFLICT (bootstrap_id) DO NOTHING;

COMMIT;
