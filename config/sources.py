"""
config/sources.py

Source configuration manager - Postgres-backed.

Responsible for loading and saving monitored sources. Keeps the exact
same public function signatures the JSON-backed version had
(load_sources/save_sources/add_source/remove_source/update_source), so
nothing above this module - MonitoringController, interface_web/app.py,
interface_streamlit/app.py, scripts/run_scheduled.py - needs to change.
Each dict returned/accepted here matches core.source.Source's own fields
one-to-one (see config/schema.sql).
"""

from __future__ import annotations

from uuid import uuid4

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from config.db import get_connection


def load_sources() -> list[dict]:

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:

            cur.execute(
                "SELECT id, name, provider, url, enabled, category, "
                "description, tags, config "
                "FROM sources ORDER BY category, name"
            )

            return cur.fetchall()


def save_sources(sources: list[dict]) -> None:
    """
    Replaces the entire sources table with the given list. Kept for
    compatibility with the old JSON-backed signature; add_source/
    remove_source/update_source below do a single-row change instead and
    are the preferred entry points for normal use.
    """

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("DELETE FROM sources")

            for source in sources:
                _insert(cur, source)


def add_source(source: dict) -> None:

    if not isinstance(source, dict):
        raise ValueError("Source must be a dictionary.")

    with get_connection() as conn:
        with conn.cursor() as cur:

            # evita duplicidade por URL, mesmo comportamento da versão JSON
            cur.execute(
                "SELECT 1 FROM sources WHERE url = %s",
                (source.get("url"),),
            )

            if cur.fetchone() is not None:
                return

            _insert(cur, source)


def remove_source(source_name) -> None:

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                "DELETE FROM sources WHERE name = %s",
                (source_name,),
            )


def update_source(old_name, new_source) -> None:

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                """
                UPDATE sources SET
                    name = %s, provider = %s, url = %s, enabled = %s,
                    category = %s, description = %s, tags = %s, config = %s
                WHERE name = %s
                """,
                (
                    new_source.get("name"),
                    new_source.get("provider"),
                    new_source.get("url"),
                    new_source.get("enabled", True),
                    new_source.get("category"),
                    new_source.get("description"),
                    Jsonb(new_source.get("tags") or []),
                    Jsonb(new_source.get("config") or {}),
                    old_name,
                ),
            )


def _insert(cur, source: dict) -> None:

    cur.execute(
        """
        INSERT INTO sources (id, name, provider, url, enabled, category, description, tags, config)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (name) DO NOTHING
        """,
        (
            source.get("id") or str(uuid4()),
            source.get("name"),
            source.get("provider"),
            source.get("url"),
            source.get("enabled", True),
            source.get("category"),
            source.get("description"),
            Jsonb(source.get("tags") or []),
            Jsonb(source.get("config") or {}),
        ),
    )
