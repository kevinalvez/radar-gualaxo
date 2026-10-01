"""
config/schedule.py

Orchestration configuration - Postgres-backed - decides WHICH keywords,
sources and search period an unattended run should use, kept independent
from whatever's selected in the Busca/Resultados tabs for a one-off run.

Note on "custom" + a recurring schedule: a fixed start_date/end_date
applies to *every* future automatic run, not a rolling window - if the
periodicity is "every 2 days" but the period is a fixed custom range,
every run searches that same historical range again. That's what was
asked for; it's just worth knowing going in, since it doesn't behave like
"24h"/"7_days"/"30_days" do (those already always mean "relative to
whenever this particular run happens").

Two mutually exclusive periodicity modes (picked via "mode"):
    "interval" - every interval_days days
    "weekdays" - on specific days of the week (weekdays), every week

WHEN a scheduled run actually fires is no longer decided by this module -
that moved to GitHub Actions' own cron
(.github/workflows/orquestracao.yml). "mode"/"interval_days"/"weekdays"/
"time" are kept here only so the Agendamento tab's existing fields still
have somewhere to live; scripts/run_scheduled.py (what the GitHub Actions
workflow actually runs) only reads "period"/"start_date"/"end_date"/
"keywords"/"sources" - the WHAT, not the WHEN.

Stored as a single row (id = 1) in the schedule table - same "one JSON
object" shape config/data/schedule.json used to hold, so this can stay
the single source of truth even if orchestration settings get edited
from more than one place.
"""

from __future__ import annotations

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from config.db import get_connection

DEFAULT = {
    "mode": "interval",
    "interval_days": None,
    "weekdays": [],
    "time": None,
    "period": "7_days",
    "start_date": None,
    "end_date": None,
    "keywords": [],
    "sources": [],
}


def load_schedule() -> dict:

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:

            cur.execute(
                "SELECT mode, interval_days, weekdays, time, period, "
                "start_date, end_date, keywords, sources "
                "FROM schedule WHERE id = 1"
            )

            row = cur.fetchone()

    if row is None:
        return dict(DEFAULT)

    return {**DEFAULT, **row}


def save_schedule(schedule: dict) -> None:

    merged = {**DEFAULT, **schedule}

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                INSERT INTO schedule
                    (id, mode, interval_days, weekdays, time, period, start_date, end_date, keywords, sources)
                VALUES
                    (1, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    mode = EXCLUDED.mode,
                    interval_days = EXCLUDED.interval_days,
                    weekdays = EXCLUDED.weekdays,
                    time = EXCLUDED.time,
                    period = EXCLUDED.period,
                    start_date = EXCLUDED.start_date,
                    end_date = EXCLUDED.end_date,
                    keywords = EXCLUDED.keywords,
                    sources = EXCLUDED.sources
                """,
                (
                    merged["mode"],
                    merged["interval_days"],
                    Jsonb(merged["weekdays"]),
                    merged["time"],
                    merged["period"],
                    merged["start_date"],
                    merged["end_date"],
                    Jsonb(merged["keywords"]),
                    Jsonb(merged["sources"]),
                ),
            )
