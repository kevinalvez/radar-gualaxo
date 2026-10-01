"""
config/migrate_json_to_db.py

One-off script: imports the existing config/data/sources.json,
config/data/keywords.json and config/data/schedule.json into Postgres.
Run config/schema.sql against the database first.

Goes through add_source()/add_keyword()/save_schedule() - the same entry
points the app itself uses - so it's safe to re-run (duplicates are
skipped the same way the UI would skip them) and doesn't need its own
separate insert logic.

Usage, once DATABASE_URL is set (see .env.example):

    python -m config.migrate_json_to_db
"""

from __future__ import annotations

from config.json_storage import load_json
from config.sources import add_source
from config.keywords import add_keyword
from config.schedule import save_schedule


def migrate() -> None:

    sources = load_json("sources.json")
    migrated_sources = 0

    for source in sources:
        if isinstance(source, dict):
            add_source(source)
            migrated_sources += 1

    print(f"Fontes migradas: {migrated_sources}")

    keywords = load_json("keywords.json")
    migrated_keywords = 0

    for keyword in keywords:
        if isinstance(keyword, str):
            add_keyword(keyword)
            migrated_keywords += 1

    print(f"Keywords migradas: {migrated_keywords}")

    schedule = load_json("schedule.json")

    if isinstance(schedule, dict) and schedule:
        save_schedule(schedule)
        print("Agendamento migrado.")
    else:
        print("Nenhum agendamento salvo em schedule.json - nada a migrar.")


if __name__ == "__main__":
    migrate()
