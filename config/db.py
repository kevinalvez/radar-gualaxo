"""
config/db.py

Postgres connection helper. Every config/*.py module (sources, keywords,
schedule) and scripts/run_scheduled.py goes through get_connection()
instead of opening its own - one place to know how the connection is
configured.

DATABASE_URL is read from the environment - always the same single code
path, regardless of where this runs:
    - Locally: a .env file (copy .env.example) is loaded automatically
      via python-dotenv.
    - Streamlit Community Cloud: interface_streamlit/app.py copies
      st.secrets["DATABASE_URL"] into os.environ before anything else in
      the app runs.
    - GitHub Actions: the workflow (.github/workflows/orquestracao.yml)
      sets it directly from a repository secret.
"""

from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg
from dotenv import load_dotenv

load_dotenv()


def _database_url() -> str:

    url = os.environ.get("DATABASE_URL")

    if not url:
        raise RuntimeError(
            "DATABASE_URL não configurada. Defina num .env local "
            "(veja .env.example), nos Secrets do app no Streamlit Cloud, "
            "ou nos Secrets do repositório no GitHub Actions."
        )

    return url


@contextmanager
def get_connection():
    """
    Yields a psycopg connection - commits on a clean exit, rolls back and
    re-raises on an exception, always closes.
    """

    connection = psycopg.connect(_database_url())

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
