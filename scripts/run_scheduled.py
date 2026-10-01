"""
scripts/run_scheduled.py

Headless entry point for the scheduled/unattended run - what GitHub
Actions' cron workflow (.github/workflows/orquestracao.yml) actually
invokes. Reads config/schedule.py (the same source of truth the
Streamlit app's Agendamento tab writes to), runs the Pipeline, and sends
the resulting clipping via Green API - no UI involved, no process needs
to stay alive between runs.

Equivalent to interface_web/app.py's _run_orchestrated_job(), but
triggered by GitHub Actions' own cron instead of an in-process
APScheduler - works even though nothing is "awake" serving a UI between
runs (a free-tier Streamlit app can be asleep and it wouldn't matter).

Usage:
    python -m scripts.run_scheduled
"""

from __future__ import annotations

import sys

from config.schedule import load_schedule
from config.sources import load_sources
from core.pipeline import Pipeline
from core.source import Source
from integrations.green_api import GreenApiError, send_whatsapp_message
from outputs.whatsapp import WhatsAppOutput
from processors.keyword import KeywordProcessor
from processors.summary import SummaryProcessor
from providers.html.provider import HTMLProvider
from providers.rss.provider import RSSProvider


def _build_sources(selected_names: set[str]) -> list[Source]:

    sources = []

    for item in load_sources():

        if not item.get("enabled", True):
            continue

        if item.get("name") not in selected_names:
            continue

        sources.append(Source.from_dict(item))

    return sources


def _build_date_filter(schedule: dict) -> dict:

    period = schedule.get("period") or "7_days"

    if period == "custom":
        return {
            "period": "custom",
            "start_date": schedule.get("start_date"),
            "end_date": schedule.get("end_date"),
        }

    return {"period": period}


def main() -> int:

    schedule = load_schedule()
    keywords = schedule.get("keywords") or []
    selected_sources = set(schedule.get("sources") or [])

    if not keywords or not selected_sources:
        print("Agendamento sem keywords/fontes configuradas - nada a fazer.")
        return 0

    sources = _build_sources(selected_sources)

    if not sources:
        print("Nenhuma fonte habilitada entre as selecionadas - nada a fazer.")
        return 0

    pipeline = Pipeline(
        providers={"rss": RSSProvider(), "html": HTMLProvider()},
        processors=[KeywordProcessor(keywords), SummaryProcessor()],
        outputs=[],
    )

    processed = pipeline.run(sources, date_filter=_build_date_filter(schedule))
    matched = [item for item in processed if item.keyword_results()]

    print(f"Publicações coletadas: {len(processed)} | Com match: {len(matched)}")

    if not matched:
        print("Nenhum resultado com match - nada a enviar.")
        return 0

    text = WhatsAppOutput(target="").build_message(matched)

    try:
        send_whatsapp_message(text)
        print("Clipping enviado via Green API.")
    except GreenApiError as error:
        print(f"Erro ao enviar via Green API: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
