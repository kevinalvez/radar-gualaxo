"""
config/keywords.py

Keyword configuration manager - Postgres-backed.

Keywords are stored as a flat list of plain strings (unquoted keywords do
AND-of-tokens matching, "quoted phrases" do substring matching - see
processors/keyword.py) - same shape config/data/keywords.json used to
hold, matching KeywordProcessor's actual expectations. Public function
signatures are unchanged from the JSON-backed version.
"""

from __future__ import annotations

from config.db import get_connection


def load_keywords() -> list[str]:

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("SELECT value FROM keywords ORDER BY value")

            return [row[0] for row in cur.fetchall()]


def save_keywords(keywords: list[str]) -> None:

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute("DELETE FROM keywords")

            cur.executemany(
                "INSERT INTO keywords (value) VALUES (%s) ON CONFLICT DO NOTHING",
                [(keyword,) for keyword in keywords],
            )


def add_keyword(keyword: str) -> None:

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                "INSERT INTO keywords (value) VALUES (%s) ON CONFLICT DO NOTHING",
                (keyword,),
            )


def remove_keyword(keyword_name: str) -> None:

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                "DELETE FROM keywords WHERE value = %s",
                (keyword_name,),
            )


def update_keyword(old_name, new_keyword) -> None:

    with get_connection() as conn:
        with conn.cursor() as cur:

            cur.execute(
                "UPDATE keywords SET value = %s WHERE value = %s",
                (new_keyword, old_name),
            )
