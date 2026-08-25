"""
interface_web/app.py

Proof-of-concept web interface, evaluated as an alternative to the
PySide6 desktop app: single Flask process, server-rendered HTML
(Jinja2), no separate JSON API/SPA split. Reuses core/, providers/,
processors/ and outputs/ unchanged - only this interface layer is new.

Job state is scoped per browser session (a signed cookie, no login) so
two people opening the intranet URL at once each get their own
"instance" of a monitoring run without interfering with each other.
Kept in memory for this prototype - fine for a single-process
intranet tool, would move to a shared store only if the process ever
needs to run behind more than one worker.

Run with: python -m interface_web.app
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from flask import Flask, render_template, request, jsonify, session, send_file
from openpyxl import Workbook

from config.sources import load_sources, add_source, remove_source, update_source
from config.keywords import load_keywords, add_keyword, remove_keyword
from config.schedule import load_schedule, save_schedule
from core.source import Source
from core.pipeline import Pipeline

from providers.rss.provider import RSSProvider
from providers.html.provider import HTMLProvider
from processors.keyword import KeywordProcessor
from processors.summary import SummaryProcessor
from outputs.json import JsonOutput

app = Flask(__name__)

# Signs the session cookie. Fine as a hardcoded dev value for an
# intranet proof of concept - would need to become a real secret
# (env var, not committed) before this leaves "prototype" status.
app.secret_key = "dev-only-change-me"

# session_id -> job state dict. One in-flight job per session at a
# time: starting a new run overwrites the previous entry for that
# session, matching "each browser session is its own instance."
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WPPSENDER_SCRIPT = PROJECT_ROOT / "wppsender" / "send_clipping.py"
CLIPPING_TO_SEND_FILE = PROJECT_ROOT / "output" / "clipping_to_send.txt"

# In-process scheduler for the Orquestração tab's unattended runs - see
# _reschedule_orchestration(). Only fires while this Flask process is
# alive; no separate OS-level scheduler involved (deliberate choice for
# now - see readme.md).
scheduler = BackgroundScheduler()
ORCHESTRATION_JOB_ID = "orchestration_run"
ORCHESTRATION_STATE: dict = {
    "next_run_at": None,
    "last_run_at": None,
    "last_run_count": None,
    "last_run_error": None,
}

# APScheduler's own CronTrigger day_of_week codes - kept as the format
# config/data/schedule.json stores "weekdays" in too, so no translation
# step is needed between the saved setting and the trigger built from it.
WEEKDAY_CODES = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")

# Same period options as the Busca tab's radios - reused as-is by
# Pipeline.run(date_filter=...) for orchestrated runs too.
VALID_PERIODS = ("24h", "7_days", "30_days")


def _display_url(url: str) -> str:
    """
    Strips the protocol and a leading "www." for a shorter, more
    scannable link column (e.g. "https://www.esbrasil.com.br/" ->
    "esbrasil.com.br"). Purely cosmetic - the real url stays the
    href/source-of-truth, this is only ever shown as label text.
    """

    display = re.sub(r"^https?://(www\.)?", "", url or "")
    return display.rstrip("/")


def _to_iso_date(value: str | None) -> str:
    """
    "DD/MM/YYYY" -> "YYYY-MM-DD", for pre-filling an <input type="date">
    from a value stored in Pipeline.filter_by_date's own format. Returns
    "" (not None) for anything that isn't a clean DD/MM/YYYY string, so
    it's always safe to drop straight into a Jinja `value="..."`.
    """

    if not value or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        return ""

    day, month, year = value.split("/")
    return f"{year}-{month}-{day}"


def _build_sources(selected_names: set[str]) -> list[Source]:
    sources = []
    for item in load_sources():
        if not isinstance(item, dict):
            continue
        if not item.get("enabled", True):
            continue
        if item.get("name") not in selected_names:
            continue
        sources.append(Source.from_dict(item))
    return sources


def _create_pipeline(keywords: list[str]) -> Pipeline:
    providers = {"rss": RSSProvider(), "html": HTMLProvider()}
    processors = [KeywordProcessor(keywords), SummaryProcessor()]
    outputs = [JsonOutput("output/results.json")]
    return Pipeline(providers, processors, outputs)


def _build_date_filter(data: dict) -> tuple[dict | None, str | None]:
    """
    Builds a Pipeline-ready date_filter from a request payload (shared by
    /run and /orchestration/save, which both offer the same period
    choices). Returns (date_filter, error_message) - error_message is
    None on success.
    """

    period = data.get("period") or "7_days"

    if period == "custom":
        start_date = (data.get("start_date") or "").strip()
        end_date = (data.get("end_date") or "").strip()

        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", start_date) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", end_date):
            return None, "Informe a data inicial e final do período específico."

        return {"period": "custom", "start_date": start_date, "end_date": end_date}, None

    if period not in VALID_PERIODS:
        return None, "Período inválido."

    return {"period": period}, None


def _run_job(session_id: str, selected_sources: set[str], selected_keywords: list[str], date_filter: dict) -> None:
    job = JOBS[session_id]

    def on_progress(done, total):
        job["progress"] = {"done": done, "total": total}

    try:
        job["status"] = "running"

        sources = _build_sources(selected_sources)
        job["log"].append(f"{len(sources)} fontes selecionadas.")

        pipeline = _create_pipeline(selected_keywords)

        processed = pipeline.run(sources, date_filter=date_filter, on_progress=on_progress)

        results = []
        for item in processed:
            kw_results = item.keyword_results()
            if not kw_results:
                continue

            summary = ""
            for result in item.results:
                if result.type == "summary":
                    summary = result.value

            category = kw_results[0].metadata.get("category") or item.publication.category or "Outros Temas"
            emoji = kw_results[0].metadata.get("emoji", "📌")

            results.append({
                "title": item.publication.title,
                "source": item.publication.source_name,
                "url": item.publication.url,
                "category": category,
                "emoji": emoji,
                "keywords": sorted({r.value for r in kw_results}),
                "summary": summary,
                "date": item.publication.publication_date.strftime("%d/%m/%Y %H:%M") if item.publication.publication_date else None,
            })

        job["results"] = results
        job["log"].append(f"Concluido: {len(results)} publicacoes com match, de {len(processed)} coletadas.")
        job["status"] = "done"

    except Exception as e:
        job["log"].append(f"Erro: {e}")
        job["status"] = "error"


def _run_orchestrated_job() -> None:
    """
    The scheduled job itself: builds the Pipeline from whatever's saved
    in config/data/schedule.json ("keywords"/"sources", independent from
    any browser session's own selection) and runs it unattended.

    Not tied to a browser session - there's no JOBS entry for this, no
    live progress in any tab. Writes to output/results.json (via
    JsonOutput, same as every other run) and to ORCHESTRATION_STATE
    (surfaced by /orchestration/status) so the Orquestração tab can at
    least show when the last automatic run happened and how it went.
    """

    schedule = load_schedule()
    keywords = schedule.get("keywords") or []
    selected_sources = set(schedule.get("sources") or [])
    period = schedule.get("period") or "7_days"

    if not keywords or not selected_sources:
        ORCHESTRATION_STATE["last_run_error"] = "Agendamento sem keywords/fontes configuradas."
        return

    if period == "custom":
        date_filter = {
            "period": "custom",
            "start_date": schedule.get("start_date"),
            "end_date": schedule.get("end_date"),
        }
    else:
        date_filter = {"period": period}

    try:
        sources = _build_sources(selected_sources)
        pipeline = _create_pipeline(keywords)

        processed = pipeline.run(sources, date_filter=date_filter)

        ORCHESTRATION_STATE["last_run_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ORCHESTRATION_STATE["last_run_count"] = len(processed)
        ORCHESTRATION_STATE["last_run_error"] = None

    except Exception as e:
        ORCHESTRATION_STATE["last_run_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        ORCHESTRATION_STATE["last_run_error"] = str(e)


def _next_run_time(time_str: str) -> datetime:
    hour, minute = (int(part) for part in time_str.split(":"))
    now = datetime.now()
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if candidate <= now:
        candidate += timedelta(days=1)

    return candidate


def _reschedule_orchestration() -> None:
    """
    (Re)schedules the orchestration job from whatever's currently saved
    - called once at startup and again every time /orchestration/save
    writes a new schedule, so config/data/schedule.json stays the single
    source of truth (editing it in the UI takes effect immediately,
    nothing needs mirroring into a second system like Windows Task
    Scheduler).

    Builds one of two trigger types depending on "mode":
        "interval" - IntervalTrigger, anchored to the requested time of
                      day via an explicit start_date (otherwise it would
                      start counting from whatever moment this happens
                      to run at)
        "weekdays"  - CronTrigger with day_of_week - naturally a "once a
                      week on these days" trigger, no anchor date needed
    """

    if scheduler.get_job(ORCHESTRATION_JOB_ID):
        scheduler.remove_job(ORCHESTRATION_JOB_ID)

    schedule = load_schedule()
    mode = schedule.get("mode") or "interval"
    time_value = schedule.get("time")

    if not time_value:
        ORCHESTRATION_STATE["next_run_at"] = None
        return

    hour, minute = (int(part) for part in time_value.split(":"))

    if mode == "weekdays":
        weekdays = [day for day in (schedule.get("weekdays") or []) if day in WEEKDAY_CODES]

        if not weekdays:
            ORCHESTRATION_STATE["next_run_at"] = None
            return

        trigger = CronTrigger(day_of_week=",".join(weekdays), hour=hour, minute=minute)

    else:
        interval_days = schedule.get("interval_days")

        if not interval_days:
            ORCHESTRATION_STATE["next_run_at"] = None
            return

        trigger = IntervalTrigger(days=interval_days, start_date=_next_run_time(time_value))

    job = scheduler.add_job(
        _run_orchestrated_job,
        trigger=trigger,
        id=ORCHESTRATION_JOB_ID,
        replace_existing=True,
    )

    ORCHESTRATION_STATE["next_run_at"] = (
        job.next_run_time.strftime("%d/%m/%Y %H:%M:%S") if job.next_run_time else None
    )


scheduler.start()
_reschedule_orchestration()


@app.route("/")
def index():
    all_sources = [item for item in load_sources() if isinstance(item, dict)]
    all_sources.sort(key=lambda item: (item.get("category") or "", item.get("name") or ""))

    for item in all_sources:
        item["display_url"] = _display_url(item.get("url", ""))

    enabled_sources = [item for item in all_sources if item.get("enabled", True)]

    categories = sorted({
        item["category"]
        for item in all_sources
        if item.get("category")
    })

    keywords = load_keywords()
    schedule = load_schedule()

    # <input type="date"> needs "YYYY-MM-DD" - the saved value is
    # "DD/MM/YYYY" (matching what Pipeline.filter_by_date expects), so
    # it's reformatted just for pre-filling the form, not stored this way.
    schedule["start_date_iso"] = _to_iso_date(schedule.get("start_date"))
    schedule["end_date_iso"] = _to_iso_date(schedule.get("end_date"))

    return render_template(
        "index.html",
        sources=enabled_sources,
        all_sources=all_sources,
        categories=categories,
        keywords=keywords,
        schedule=schedule,
    )


@app.route("/keywords/add", methods=["POST"])
def keywords_add():
    data = request.get_json(force=True)
    value = (data.get("value") or "").strip()

    if not value:
        return jsonify({"error": "Informe uma keyword."}), 400

    add_keyword(value)
    return jsonify({"ok": True})


@app.route("/keywords/remove", methods=["POST"])
def keywords_remove():
    data = request.get_json(force=True)
    value = (data.get("value") or "").strip()

    remove_keyword(value)
    return jsonify({"ok": True})


@app.route("/sources/add", methods=["POST"])
def sources_add():
    data = request.get_json(force=True)

    name = (data.get("name") or "").strip()
    url = (data.get("url") or "").strip()

    if not name or not url:
        return jsonify({"error": "Nome e URL são obrigatórios."}), 400

    add_source({
        "name": name,
        "provider": data.get("provider") or "html",
        "url": url,
        "enabled": bool(data.get("enabled", True)),
        "category": (data.get("category") or "").strip(),
        "description": (data.get("description") or "").strip(),
    })

    return jsonify({"ok": True})


@app.route("/sources/toggle", methods=["POST"])
def sources_toggle():
    data = request.get_json(force=True)
    name = data.get("name")

    source = next((s for s in load_sources() if isinstance(s, dict) and s.get("name") == name), None)

    if source is None:
        return jsonify({"error": "Fonte não encontrada."}), 404

    updated = dict(source)
    updated["enabled"] = not source.get("enabled", True)
    update_source(name, updated)

    return jsonify({"ok": True, "enabled": updated["enabled"]})


@app.route("/sources/remove", methods=["POST"])
def sources_remove():
    data = request.get_json(force=True)
    remove_source(data.get("name"))
    return jsonify({"ok": True})


@app.route("/orchestration/save", methods=["POST"])
def orchestration_save():
    data = request.get_json(force=True)

    mode = data.get("mode") or "interval"
    if mode not in ("interval", "weekdays"):
        return jsonify({"error": "Modo de periodicidade inválido."}), 400

    time_value = (data.get("time") or "").strip()
    if not re.fullmatch(r"[0-2]\d:[0-5]\d", time_value):
        return jsonify({"error": "Informe um horário válido (HH:MM)."}), 400

    date_filter, error = _build_date_filter(data)
    if error:
        return jsonify({"error": error}), 400

    keywords = data.get("keywords") or []
    sources = data.get("sources") or []

    if not keywords:
        return jsonify({"error": "Selecione ao menos uma keyword para a orquestração."}), 400

    if not sources:
        return jsonify({"error": "Selecione ao menos uma fonte para a orquestração."}), 400

    schedule = {
        "mode": mode,
        "time": time_value,
        "period": date_filter["period"],
        "start_date": date_filter.get("start_date"),
        "end_date": date_filter.get("end_date"),
        "keywords": keywords,
        "sources": sources,
        "interval_days": None,
        "weekdays": [],
    }

    if mode == "weekdays":
        weekdays = [day for day in (data.get("weekdays") or []) if day in WEEKDAY_CODES]

        if not weekdays:
            return jsonify({"error": "Selecione ao menos um dia da semana."}), 400

        schedule["weekdays"] = weekdays

    else:
        try:
            interval_days = int(data.get("interval_days"))
            if interval_days < 1:
                raise ValueError
        except (TypeError, ValueError):
            return jsonify({"error": "Informe um número de dias válido (mínimo 1)."}), 400

        schedule["interval_days"] = interval_days

    save_schedule(schedule)

    _reschedule_orchestration()

    return jsonify({"ok": True, "next_run_at": ORCHESTRATION_STATE["next_run_at"]})


@app.route("/orchestration/status")
def orchestration_status():
    return jsonify(ORCHESTRATION_STATE)


@app.route("/run", methods=["POST"])
def run():
    data = request.get_json(force=True)
    selected_sources = set(data.get("sources", []))
    selected_keywords = data.get("keywords", [])

    if not selected_keywords:
        return jsonify({"error": "Selecione ao menos uma keyword."}), 400

    date_filter, error = _build_date_filter(data)
    if error:
        return jsonify({"error": error}), 400

    session.setdefault("session_id", str(uuid.uuid4()))
    session_id = session["session_id"]

    with JOBS_LOCK:
        JOBS[session_id] = {
            "status": "starting",
            "progress": {"done": 0, "total": 0},
            "log": [],
            "results": [],
            "started_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        }

    thread = threading.Thread(
        target=_run_job,
        args=(session_id, selected_sources, selected_keywords, date_filter),
        daemon=True,
    )
    thread.start()

    return jsonify({"ok": True})


@app.route("/status")
def status():
    session_id = session.get("session_id")
    if session_id is None or session_id not in JOBS:
        return jsonify({"status": "idle"})
    return jsonify(JOBS[session_id])


def _build_clipping_text(results: list[dict]) -> str:
    categories: dict[str, dict] = {}
    for item in results:
        bucket = categories.setdefault(item["category"], {"emoji": item["emoji"], "items": []})
        bucket["items"].append(item)

    lines = [
        "📌 *Clipping – Radar Gualaxo*",
        f"📅 *{datetime.now().strftime('%d/%m/%Y')}*",
        "",
    ]

    for category, bucket in categories.items():
        lines.append(f"{bucket['emoji']} *{category}*")
        lines.append("")
        for item in bucket["items"]:
            lines.append(f"• {item['title']}")
            lines.append(f"   o Veículo: {item['source']}")
            lines.append(f"   o Link: {item['url']}")
            if item["summary"]:
                lines.append(f"   o Resumo: {item['summary']}")
            lines.append("")

    return "\n".join(lines)


def _current_job_results() -> list[dict] | None:
    session_id = session.get("session_id")
    job = JOBS.get(session_id) if session_id else None

    if not job or job.get("status") != "done" or not job.get("results"):
        return None

    return job["results"]


@app.route("/clipping")
def clipping():
    results = _current_job_results()

    if results is None:
        return jsonify({"error": "Rode o monitoramento antes de gerar o clipping."}), 400

    return jsonify({"text": _build_clipping_text(results)})


@app.route("/results/export.xlsx")
def results_export_xlsx():
    results = _current_job_results()

    if results is None:
        return jsonify({"error": "Rode o monitoramento antes de exportar."}), 400

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Resultados"

    header = ["Título", "Veículo", "Categoria", "Data", "Keywords", "Resumo", "Link"]
    sheet.append(header)

    for item in results:
        sheet.append([
            item["title"],
            item["source"],
            item["category"],
            item.get("date") or "",
            ", ".join(item["keywords"]),
            item.get("summary") or "",
            item["url"],
        ])

    # Reasonable column widths - long free-text columns (título, resumo)
    # capped so the sheet doesn't render as one absurdly wide column,
    # short columns (data, categoria) left to fit their own content.
    column_widths = {"A": 50, "B": 22, "C": 28, "D": 18, "E": 24, "F": 60, "G": 45}
    for column, width in column_widths.items():
        sheet.column_dimensions[column].width = width

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    filename = f"resultados-{datetime.now().strftime('%Y-%m-%d')}.xlsx"

    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/whatsapp/send", methods=["POST"])
def whatsapp_send():
    results = _current_job_results()

    if results is None:
        return jsonify({"error": "Rode o monitoramento antes de enviar o clipping."}), 400

    if not WPPSENDER_SCRIPT.exists():
        return jsonify({"error": f"{WPPSENDER_SCRIPT} não encontrado."}), 500

    texto = _build_clipping_text(results)

    CLIPPING_TO_SEND_FILE.parent.mkdir(parents=True, exist_ok=True)
    CLIPPING_TO_SEND_FILE.write_text(texto, encoding="utf-8")

    # Fire-and-forget: opens a real (visible) Chrome window on this
    # machine via Selenium and can take a while (first run needs a QR
    # code scan) - not something to block this HTTP request on. No
    # progress is streamed back today; success/failure is only visible
    # in that Chrome window and this process's own stdout.
    subprocess.Popen(
        [sys.executable, str(WPPSENDER_SCRIPT), "--file", str(CLIPPING_TO_SEND_FILE)],
        cwd=str(PROJECT_ROOT),
    )

    return jsonify({"ok": True})


def start():
    app.run(host="0.0.0.0", port=5000, threaded=True)


if __name__ == "__main__":
    start()
