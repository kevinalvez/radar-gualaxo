-- config/schema.sql
--
-- Tables config/sources.py, config/keywords.py and config/schedule.py
-- read from - mirrors the shape config/data/*.json used to hold before
-- the move to Postgres. Run once against the target database:
--
--     psql "$DATABASE_URL" -f config/schema.sql
--
-- then port existing data over with `python -m config.migrate_json_to_db`
-- (reads from config/data/*.json, so run it before those files are
-- deleted/stop being updated).

CREATE TABLE IF NOT EXISTS sources (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    provider    TEXT NOT NULL,
    url         TEXT NOT NULL,
    enabled     BOOLEAN NOT NULL DEFAULT TRUE,
    category    TEXT,
    description TEXT,
    tags        JSONB NOT NULL DEFAULT '[]'::jsonb,
    config      JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS keywords (
    value TEXT PRIMARY KEY
);

-- Single-row table (id is always 1) - same "one JSON object" shape
-- config/data/schedule.json used to hold. "mode"/"interval_days"/
-- "weekdays"/"time" are kept for backward compatibility with the
-- Orquestração tab's own fields even though the actual trigger is now
-- GitHub Actions' own cron (.github/workflows/orquestracao.yml) - this
-- table is what decides WHICH keywords/sources/period a scheduled run
-- uses, not WHEN it runs.
CREATE TABLE IF NOT EXISTS schedule (
    id            INTEGER PRIMARY KEY DEFAULT 1,
    mode          TEXT NOT NULL DEFAULT 'interval',
    interval_days INTEGER,
    weekdays      JSONB NOT NULL DEFAULT '[]'::jsonb,
    time          TEXT,
    period        TEXT NOT NULL DEFAULT '7_days',
    start_date    TEXT,
    end_date      TEXT,
    keywords      JSONB NOT NULL DEFAULT '[]'::jsonb,
    sources       JSONB NOT NULL DEFAULT '[]'::jsonb,
    CONSTRAINT schedule_singleton CHECK (id = 1)
);
