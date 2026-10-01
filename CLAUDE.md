# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Radar Gualaxo monitors RSS/HTML sources for keywords and produces reports (JSON/CSV/WhatsApp clipping text). It's a personal/early-stage project (Portuguese comments and debug prints are mixed into the English codebase) built around a strict pipeline architecture: **collection is independent from processing**. See `readme.md` for full detail; this file is the condensed version for day-to-day edits.

It ships four interchangeable interfaces driving the same `core/` Pipeline:

- `interface_streamlit/` — Streamlit, **the target hosted deployment** (Streamlit Community Cloud, free tier — no server of the project owner's own to keep running). Run locally with `streamlit run interface_streamlit/app.py`. Reuses `core/`, `providers/`, `processors/`, `outputs/`, `config/`, `integrations/` unchanged — only this presentation layer is new. Still under active build-out; see "Hosted stack" below for the storage/scheduling/WhatsApp pieces it depends on.
- `interface_web/` — Flask + Jinja2, the original v1 target (self-hosted, e.g. on a machine on the local network). Run explicitly with `python -m interface_web.app` (binds `0.0.0.0:5000`).
- `interface_qt/` — PySide6 desktop app, still `main.py`'s default entry point (`python main.py`).
- `legacy/interface/` — the original Tkinter desktop app. Fully legacy: kept only for rollback safety, not run or maintained day-to-day. `legacy/prototypes/` (throwaway UI comparisons) and `legacy/wppsender_old/` (an older, unrelated mass-send script superseded by `wppsender/send_clipping.py`) are legacy for the same reason — none of `legacy/` is wired into the app or imported by anything outside itself.

## Running the app

```
streamlit run interface_streamlit/app.py    # Streamlit interface (needs DATABASE_URL — see Hosted stack)
python -m interface_web.app                 # Flask web interface, http://<host>:5000
python main.py                              # PySide6 desktop interface (default entry point, unchanged on purpose)
```

There is no CLI/headless monitoring mode for ad-hoc runs — `main()` in `main.py` builds a pipeline but is dead code. `scripts/run_scheduled.py` (`python -m scripts.run_scheduled`) *is* a real headless entry point, but it's specifically the scheduled/unattended run (reads `config/schedule.py`, sends via Green API) — see "Hosted stack" below.

Install dependencies (PySide6 is commented out in `requirements.txt` since a server/Streamlit Cloud deployment doesn't need it):

```
pip install -r requirements.txt
```

`wppsender/` (Selenium-based WhatsApp sender, superseded by `integrations/green_api.py` for anything running headless/hosted — still useful for a local, display-having machine) has its own separate `wppsender/requirements.txt`.

## Hosted stack (Streamlit + Postgres + Green API + GitHub Actions)

The project is migrating from "self-hosted on a machine the owner keeps running" to a fully free, hosted setup. Four pieces, each replacing one specific constraint of the old setup:

- **Storage — Postgres (`config/db.py`, `config/schema.sql`)**, hosted on Railway. Replaces `config/data/*.json`: `interface_web`'s JSON files only work on a machine with a persistent disk, which Streamlit Community Cloud's free tier doesn't give (the container resets from the Git repo on every sleep/redeploy). `config/sources.py`/`config/keywords.py`/`config/schedule.py` were rewritten to read/write Postgres instead of JSON, keeping their exact previous public function signatures (`load_sources`/`add_source`/`remove_source`/`update_source`, `load_keywords`/`add_keyword`/`remove_keyword`/`update_keyword`, `load_schedule`/`save_schedule`) — so `interface_web/`, `interface_qt/` and `legacy/interface/` all keep working against the same storage with zero changes of their own, they just now also need `DATABASE_URL` set to run at all. Apply `config/schema.sql` once against a fresh database, then port existing JSON data over with `python -m config.migrate_json_to_db` (reads `config/data/*.json`, calls the same `add_source`/`add_keyword`/`save_schedule` the app itself uses — safe to re-run). `config/json_storage.py` still exists (the migration script reads through it) but nothing in `config/` writes through it anymore.
- **WhatsApp sending — Green API (`integrations/green_api.py`)**. Replaces `wppsender/send_clipping.py`'s Selenium automation: a plain REST call (`send_whatsapp_message(text)`), no browser/display needed, so it works from Streamlit Cloud or a GitHub Actions runner. Needs `GREEN_API_ID_INSTANCE`/`GREEN_API_TOKEN`/`GREEN_API_CHAT_ID`. The free Developer plan caps at 3 distinct chats/month — this project only ever sends to one fixed group, so that's not a binding limit.
- **Scheduling — GitHub Actions (`.github/workflows/orquestracao.yml`)**. Replaces `interface_web/app.py`'s in-process `APScheduler`, which only fires while that Flask process is alive — not compatible with a Streamlit Cloud free app that sleeps when idle. The workflow's own `cron:` is the single source of truth for *when* a scheduled run fires; `config/schedule.py` (edited from the Streamlit app's Agendamento tab) still decides *what* it runs — which keywords/sources/period. The workflow runs `python -m scripts.run_scheduled` (`scripts/run_scheduled.py`), a headless script equivalent to `interface_web/app.py`'s `_run_orchestrated_job()` but triggered externally instead of by an in-process scheduler.
- **`DATABASE_URL`/`GREEN_API_*` env vars** are read the same way regardless of where the code runs — always `os.environ`, never branching on deployment target. Locally, `config/db.py` loads a `.env` file (copy `.env.example`) via `python-dotenv`. On Streamlit Cloud, `interface_streamlit/app.py` copies `st.secrets[...]` into `os.environ` once at startup, before any other module reads it. On GitHub Actions, the workflow sets them directly from repository secrets. `.env` and `.streamlit/secrets.toml` are both gitignored — never commit real credentials into either.

Not yet done: `interface_streamlit/app.py`'s Agendamento tab no longer edits *when* a scheduled run fires (that moved to the workflow's own cron) — its `mode`/`interval_days`/`weekdays`/`time` fields are kept in `config/schedule.py` for shape compatibility but aren't surfaced in that tab's UI. A results table in Postgres (the `output/results.json` replacement) is planned but not built yet — out of scope until explicitly asked for.

## No build/lint/test tooling

There are no tests, no linter config, and no build step in this repo. Don't assume `pytest`/`ruff`/etc. are configured — check before suggesting a command.

## Architecture

The core flow, enforced end-to-end, is:

```
Source → Provider → Publication → Processor → Result → ProcessedPublication → Output
```

Every stage is an abstract base class in `core/`, and concrete implementations live in sibling top-level packages. **The Pipeline (`core/pipeline.py`) should never need modification when adding a new Provider/Processor/Output** — new capabilities are added by writing a new class that implements the relevant `core/` interface, never by branching inside the Pipeline.

- `core/source.py` — `Source` dataclass: pure configuration (name, provider id, url, enabled, category, tags, config). Never performs collection itself.
- `core/provider.py` — `Provider` ABC. One method: `collect(source) -> list[Publication]`. Providers only fetch/parse; they never search keywords or judge relevance.
- `core/publication.py` — `Publication` dataclass: the central domain entity every Provider must produce, regardless of origin (RSS, HTML, future PDF/API/etc). Has `content_hash()` for future dedup and `contains()` for substring checks.
- `core/processor.py` — `Processor` ABC. One method: `process(publication) -> list[Result]`. Processors never know which Provider produced the Publication, and never touch Outputs.
- `core/result.py` — `Result` dataclass: one processing occurrence (e.g. one keyword match), with `type`, `value`, `score`, `metadata`.
- `core/processed_publication.py` — `ProcessedPublication` bundles a `Publication` with all `Result`s generated by every configured Processor; this is what gets handed to Outputs.
- `core/output.py` — `Output` ABC. One method: `export(processed_publications)`. Outputs only serialize/format; they never analyze data.
- `core/pipeline.py` — `Pipeline.run(sources, date_filter)` orchestrates: for each `Source`, look up its `Provider` by `source.provider` key in the `providers` dict, `collect()`, apply `filter_by_date()` (supports `24h`/`7_days`/`30_days`/`custom` periods), run every configured `Processor` over each `Publication`, accumulate into `ProcessedPublication`s, then call `export()` on every configured `Output`. Note: `run()` currently calls `provider.collect(source)` more than once per source (duplicated collection code left in from debugging) — be aware of this when touching that method.

### Providers (`providers/`)

- `providers/rss/provider.py` — `RSSProvider` (`name == "rss"`), built on `feedparser`. Extracts title/content/url/date/author/tags from feed entries.
- `providers/html/provider.py` — `HTMLProvider` (`name == "html"`), built on `requests` + `BeautifulSoup`. Downloads a page, discovers links (`discovery.py`), strips scripts/nav/footer (`cleaners.py`), extracts readable content (`extractor.py`), and currently produces **one Publication per crawled link** (home page + up to `max_pages` discovered links). Filters out short/malformed pages (`len(content) < 100`).

### Processors (`processors/`)

- `processors/keyword.py` — `KeywordProcessor`: takes a list of keyword configs (`{keyword, enabled, category, emoji}` or plain strings), splits publication content into paragraphs, and matches each keyword per paragraph. Quoted keywords (`"exact phrase"`) do substring match; unquoted keywords do AND-of-tokens match via `_tokenize`. Capitalization in the keyword marks a proper noun: a capitalized quoted phrase (`"Rio Doce"`) ignores all-lowercase occurrences ("água de rio doce"), and a single capitalized unquoted word (`Mariana`, `Vale`) ignores occurrences followed by another capitalized word, i.e. a person's name ("Mariana Furtado"). One `Result` per keyword match per paragraph.
- `processors/summary.py` — `SummaryProcessor`: simple extractive summarizer (first relevant sentences), not AI-based.

### Outputs (`outputs/`)

- `outputs/json.py`, `outputs/csv.py` — serialize `ProcessedPublication`s to `output/results.json` / `output/results.csv`.
- `outputs/whatsapp.py` — `WhatsAppOutput`: groups results by category (from `Result.metadata["category"]`), formats a WhatsApp-friendly clipping message grouped by emoji/category, writes to a `.txt` target.

### Configuration (`config/`)

- `config/db.py` — Postgres connection helper (`get_connection()`, a context manager over a `psycopg` connection). Reads `DATABASE_URL` from `os.environ` — see "Hosted stack" above for how that gets set depending on where the code runs.
- `config/schema.sql` — `CREATE TABLE` statements for `sources`/`keywords`/`schedule`. Apply once per database (`psql "$DATABASE_URL" -f config/schema.sql`).
- `config/sources.py`, `config/keywords.py`, `config/schedule.py` — Postgres-backed now (previously JSON-backed). Same public function signatures as before the migration, so callers above this layer didn't need to change. `sources`/`keywords` dicts match `core.source.Source`'s fields one-to-one.
- `config/migrate_json_to_db.py` — one-off script, ports `config/data/*.json` into Postgres via the same `add_source`/`add_keyword`/`save_schedule` entry points the app itself uses (`python -m config.migrate_json_to_db`).
- `config/json_storage.py` — generic `load_json`/`save_json` against `config/data/*.json`. Still used by `config/migrate_json_to_db.py` to read the old files; no longer used to persist anything.

### Integrations (`integrations/`)

- `integrations/green_api.py` — `send_whatsapp_message(text, chat_id=None)`, a thin wrapper over Green API's REST `sendMessage` endpoint. Raises `GreenApiError` on a non-2xx response or missing `GREEN_API_*` env vars.

### Scripts (`scripts/`)

- `scripts/run_scheduled.py` — headless entry point for the scheduled/unattended run (`python -m scripts.run_scheduled`). What `.github/workflows/orquestracao.yml`'s cron actually invokes: reads `config/schedule.py`, runs the Pipeline, sends the result via `integrations/green_api.py`.

### Interfaces

- `interface_streamlit/app.py` — single-file Streamlit app, tabs via `st.tabs`: Busca (run the pipeline, `st.data_editor` for per-run source selection), Resultados (`st.dataframe`), Clipping (`WhatsAppOutput.build_message()` reused for the text, send via Green API), Configuração (source/keyword CRUD), Agendamento (edits `config/schedule.py`'s *what*, not *when* — see "Hosted stack" above). `load_sources()`/`load_keywords()` are wrapped in `st.cache_data(ttl=30)`; any add/remove/update calls `_invalidate_config_cache()` before `st.rerun()` so the change shows immediately instead of waiting out the cache.
- `interface_web/app.py` — single Flask process, server-rendered HTML (no JSON API/SPA split). Tabs: Busca (run the pipeline), Resultados (sortable table + Excel export), Clipping (WhatsApp-formatted text, copy/download/send), Configuração (keyword/source CRUD), Orquestração (unattended scheduled runs via an in-process `APScheduler` — superseded by GitHub Actions for the hosted deployment, see "Hosted stack" above, but still functional here for a self-hosted run). Job state (progress/log/results) is kept in an in-memory `JOBS` dict keyed by a per-browser-session cookie, so concurrent users each get their own run. A background `threading.Thread` runs `Pipeline.run()`; the page polls `/status`.
- `interface_qt/` — PySide6. `MonitoringController` mirrors the same public API shape the old Tkinter tabs had, runs the Pipeline on a background `QThread` (`monitoring_worker.py`).
- `legacy/interface/` — original Tkinter app. `MainWindow` (`legacy/interface/main_window.py`) builds a `ttk.Notebook` with tabs: Configuration/Selection, Results, Logs, Clipping. `legacy/interface/controllers/monitoring_controller.py` is the glue between that UI and the core pipeline. Kept for rollback safety only — don't build on this, extend `interface_streamlit/`, `interface_web/` or `interface_qt/` instead.

## Conventions to preserve

- **Keep the pipeline generic.** When adding a new source type, write a new `Provider` subclass and register it in the `providers` dict passed to `Pipeline` (see `MonitoringController.create_pipeline`) — don't special-case it inside `Pipeline.run`.
- **Everything becomes a `Publication`.** Processors and Outputs must never branch on where data came from.
- Domain entities (`Publication`, `Source`, `Result`, `ProcessedPublication`) are `@dataclass(slots=True)` with `to_dict`/`from_dict`/`to_json` — follow this pattern for any new domain entity.
- `config/sources.py`/`config/keywords.py`/`config/schedule.py` (Postgres-backed) return plain dicts/strings, not domain objects; conversion to typed objects (e.g. `Source.from_dict`) happens at the boundary where they're consumed (e.g. `MonitoringController.build_sources`, `scripts/run_scheduled.py`'s `_build_sources`).
- The codebase mixes English identifiers/docstrings with Portuguese debug prints and comments (this targets Portuguese-language news sources, e.g. the Rio Doce Agreement use case). Match existing style in the file you're editing rather than forcing consistency across the whole repo.
