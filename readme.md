# Radar Gualaxo

> A modular and extensible monitoring platform for collecting, processing and organizing information from heterogeneous sources.

---

# Overview

Radar Gualaxo is a monitoring application designed to collect information from multiple sources through a modular pipeline architecture. Its primary interface is a Flask-based web app (`interface_web/` - single server process, reachable from any browser on the network), driving the same `core/` Pipeline as two legacy desktop interfaces (`interface_qt/`, PySide6; `legacy/interface/`, Tkinter) kept in the codebase but no longer actively developed.

Although the first use case is monitoring topics related to the **Rio Doce Agreement**, the project was designed to be completely domain-agnostic.

Instead of building specific collectors for each website, the platform converts every collected document into a common domain entity:

```
Publication
```

From this point forward, every processing component works exactly the same way, regardless of where the information originated.

---

# Philosophy

The project follows a very simple principle:

> Collection is independent from processing.

A Processor should never know if a publication came from:

- RSS
- HTML
- API
- Search Engine
- PDF
- Government Portal
- Official Gazette
- YouTube
- Podcast

Everything becomes a `Publication`.

This keeps the entire system loosely coupled and highly extensible.

---

# Architecture

```
Sources
    │
    ▼
Providers
    │
    ▼
Publication
    │
    ▼
Processors
    │
    ▼
ProcessedPublication
    │
    ▼
Outputs
```

---

# Web Application

`interface_web/` (Flask + Jinja2 + vanilla JS, no separate JSON API/SPA
split - server-rendered HTML, same shape as a classic PHP app) is the
primary way to run Radar Gualaxo, replacing the desktop apps. Rationale:
centralize execution on one server machine, reachable from any browser on
the local network, instead of requiring each user to run a desktop app.

Run with:

```
python -m interface_web.app
```

Then open `http://<machine-ip>:5000` from any device on the same network
(the app already binds to `0.0.0.0`; the machine's own firewall still needs
to allow inbound TCP on port 5000 - see `config.txt`).

Reuses `core/`, `providers/`, `processors/`, `outputs/` and `config/`
completely unchanged - only this presentation layer is new.

## Tabs

- **Busca** - select keywords/sources/period and run the Pipeline. Period
  includes a "período específico" option (explicit start/end dates via
  two `<input type="date">`, converted to Pipeline's own "DD/MM/YYYY"
  format client-side) alongside the fixed 24h/7 dias/30 dias choices.
  Sources are shown in a scrollable, searchable table (not a flat
  checkbox list - `sources.json` has grown past what's comfortable as
  one long list), grouped implicitly by category via server-side sort. A
  background `threading.Thread` runs `Pipeline.run()`; the page polls a
  `/status` endpoint every second for progress/log/results, so the
  request that starts the run returns immediately instead of blocking.
- **Resultados** - a sortable, searchable table of the last run's matches
  (title, source, category, date, keywords, summary), plus an "Exportar
  Excel" button (`/results/export.xlsx`) that streams a real `.xlsx`
  spreadsheet (via `openpyxl`, built in-memory - no temp file on disk)
  of the same session's results, not a CSV opened in Excel.
- **Clipping** - generates the same WhatsApp-formatted clipping text as
  the desktop apps (category grouping, emoji, summary) from the last run's
  results, with copy-to-clipboard, `.txt` download, and a confirm-gated
  "Enviar pro WhatsApp" button that writes the text to
  `output/clipping_to_send.txt` and fires
  `wppsender/send_clipping.py --file ...` as a background subprocess -
  see `wppsender/send_clipping.py` below for what that actually does
  (opens a real, visible Chrome window via Selenium on whichever machine
  runs the Flask process).
- **Configuração** - keyword management (add/remove), source management
  (add/remove/enable-disable, table view of every registered source
  including disabled ones).
- **Orquestração** - its own tab (moved out of Configuração): how often
  to run unattended - either "every N days" (`IntervalTrigger`) or
  specific weekdays picked from a dropdown checklist
  (`CronTrigger(day_of_week=...)`), both at a given HH:MM - plus its own
  search period (same 24h/7 dias/30 dias/período específico options as
  the Busca tab, chosen independently of how often it runs - though a
  fixed "período específico" combined with a recurring schedule means
  every future run re-searches that same fixed historical range, not a
  rolling window; worth knowing, not prevented) and a keyword/source
  selection *independent* from whatever's checked in the Busca tab for a
  one-off run - persisted to `config/data/schedule.json`
  (`config/schedule.py`) so it's a single file that can be the source of
  truth even if orchestration settings get edited from more than one
  machine, same reasoning as `sources.json`/`keywords.json`. Actually
  executes now: an in-process `APScheduler` `BackgroundScheduler`
  (`interface_web/app.py`) reads that same file and fires
  `Pipeline.run()` unattended - editing the schedule in the UI
  reschedules it immediately (`_reschedule_orchestration()`), no restart
  needed. The tab shows the computed next-run time and the outcome of
  the last automatic run (publications found, or the error if it
  failed). Deliberately no OS-level scheduler (Windows Task Scheduler)
  involved - see Known Limitations for the trade-off that comes with
  that choice.

## Session model

Job state (progress/log/results) is scoped per browser session (a signed
cookie, no login) via an in-memory `JOBS: dict[str, dict]` keyed by
session id - two people opening the same URL each get their own run
without interfering with each other's progress/results view. Not
concurrency-hardened beyond that: `output/results.json` and the
`config/data/*.json` files are shared, unlocked, last-writer-wins targets
- acceptable for now since `output/results.json` is explicitly a
validation-only artifact for this stage (Postgres is the planned durable
store, see Roadmap), and simultaneous config edits by two people are an
edge case at this stage's usage level.

---

# Desktop Application

The desktop interfaces are responsible only for configuration and
execution - kept in the codebase as legacy fallbacks. The web interface
above is the primary, actively developed way to run Radar Gualaxo.

```
                 Radar Gualaxo Interface

        ┌──────────────┬──────────────┐
        │              │              │
        ▼              ▼              ▼

 Configuration    Monitoring     Clipping

        │
        ▼

   Core Pipeline

        │

 ┌──────┼───────────┐

 ▼      ▼           ▼

Providers Processors Outputs
```

## Two desktop interfaces, one Pipeline

Two desktop interfaces exist in the codebase, both driving the exact same
`core/` Pipeline. Note: `python main.py` still launches the PySide6
desktop app unconditionally (that default hasn't been changed) - to run
the web interface instead, use `python -m interface_web.app` explicitly
(see Web Application above).

- `interface_qt/` — a PySide6 (Qt) interface, `main.py`'s current default
  entry point (`python main.py`, or `python -m interface_qt.app`
  directly). Not a fork
  of the app's logic, only of the presentation layer: each tab mirrors the
  same public API its Tkinter counterpart had (e.g. `ResultsTab.show_results()`,
  `ConfigurationTab.get_selected_keywords()`), so `MonitoringController`
  talks to `core/` the same way either interface would. It adds, versus the
  Tkinter version: a searchable/sortable results table, a checkable
  scrollable list for keywords *and* sources (so a run can include/exclude
  specific sources without touching `sources.json`), calendar-based date
  pickers, a background-thread pipeline run (see below) and a status-bar
  progress bar during a run.
- `legacy/interface/` — the original Tkinter interface. Still present and
  still functional (`python -c "from legacy.interface.app import start; start()"`),
  kept as a fallback for rollback safety. Not deleted; a deliberate decision
  left for the project owner, not made unilaterally.

`MonitoringController.run_monitor()` (PySide6 version) runs the Pipeline on
a background `QThread` (`interface_qt/monitoring_worker.py`) instead of
blocking the UI thread - the window stays responsive during a run, the run
button shows "Executando..." and is disabled to prevent a second concurrent
run, and `Pipeline.run()`'s optional `on_progress(current, total)` callback
drives a progress bar in the status bar (hidden when idle).

---

# Current Features

## Configuration

The application allows managing monitoring configuration without editing code.

Implemented:

- Source registration
- Source editing
- Source removal
- Keyword registration
- Keyword editing
- Keyword removal
- Keyword selection
- Enable/disable sources

Available in both the PySide6 desktop interface and the web interface's
Configuração tab. `config/keywords.py`'s `remove_keyword`/`update_keyword`
used to assume `keywords.json` stored dicts (`item["keyword"]`) and would
raise `TypeError` against the actual flat-string-list format the moment
either was invoked - fixed to operate on plain strings, matching reality.

A background-execution schedule (run every N days, at a given time, with
its own keyword/source selection) can be configured from the web
interface's own Orquestração tab (`config/schedule.py`,
`config/data/schedule.json`) and actually runs unattended via an
in-process `APScheduler` - see Web Application above.

Configuration is stored in JSON files.

---

# Sources

A Source represents a monitored information source.

It stores only configuration.

Example:

```json
{
    "name": "G1",
    "provider": "rss",
    "url": "https://g1.globo.com/dynamo/brasil/rss2.xml",
    "enabled": true,
    "category": "news",
    "description": "",
    "tags": [],
    "config": {}
}
```

Current attributes:

- id
- name
- provider
- url
- enabled
- category
- description
- tags
- config

A Source never performs collection.

`category` is not just descriptive metadata: a `Publication` inherits its
Source's `category` whenever the collected page itself doesn't expose one
(see Publication section below) - which is the common case for
institutional/government pages. That inherited category is what the
Clipping output groups by whenever the matched keyword has no category of
its own configured (see Clipping section).

`config` supports a `max_pages` key for the `html` provider, overriding its
default per-source crawl cap - see HTML Provider below.

`sources.json` currently holds 73 curated sources across ~18 categories,
spanning news outlets, official gazettes, courts, and institutional/notice
portals related to the Rio Doce Agreement.

8 originally-HTML sources (ES Brasil, Espírito Santo Notícias, Rede
Educadora, Jornal Geraes, Jornal da Cidade Vales de Minas, Jornal Bairros
Net, Sou Patos, Rádio Mundo Melhor) were switched to `provider: "rss"`
pointed at each site's `/feed/`: high-volume outlets publish enough per
day that an article can scroll off the homepage - the only page the HTML
Provider's link discovery ever looks at - before the next run happens, so
the HTML Provider structurally cannot see it even though it would extract
cleanly if it could. An RSS feed's own "most recent N items" window has
the same shape of limit, but it's a much larger and more reliable buffer
than a homepage's visible links (no nav/footer/sidebar noise diluting it).
This doesn't fix the underlying "collection is a snapshot" limitation by
itself - it needs pairing with frequent-enough runs (the Orquestração
tab's scheduling now actually executes, see Web Application) to actually
stop losing coverage.

---

# Providers

Providers are responsible only for collecting information.

Current providers:

## RSS Provider

Implemented.

Features:

- RSS feeds
- Atom feeds
- Publication date extraction
- Author extraction (when available)
- Content extraction
- URL extraction

---

## HTML Provider

Implemented. The most heavily calibrated provider - the sub-modules under
`providers/html/` split cleanly by responsibility:

- `provider.py` - orchestrates download → clean → extract/classify → build
  Publication for each discovered link.
- `discovery.py` - finds candidate links on the source page, restricted to
  the source's own domain.
- `filters.py` - URL-level filtering (ignored extensions/paths) and the
  heuristics used to prioritize links: same-section-as-source first, then
  links that structurally look like an article (a date segment in the path,
  or a long hyphenated slug) over listing/navigation-shaped links.
- `cleaners.py` - strips script/style/nav/header/footer/aside before
  extraction.
- `extractor.py` - identifies the actual content container and classifies
  it as article vs. listing/hub page.

Current responsibilities:

- Download HTML pages
- Parse HTML and strip non-content elements
- Discover same-domain links, prioritized by section relevance and
  article-like URL shape
- Identify the article's content container, even on page-builder sites
  (e.g. Elementor, or WordPress themes that reuse `<article>` for both the
  real post and short "related posts" teaser cards) - candidates from
  multiple CSS selector tiers are compared by text length rather than
  trusting the first match
- Reject a selector match that resolves to `<body>`/`<html>` itself (some
  sites put an id like `"content"` directly on `<body>`, which would
  otherwise make a generic `#content` selector "win" by matching the
  entire page - chrome, nav bars and all - since it's trivially the
  longest candidate)
- Detect and reject listing/hub pages, three independent ways: heading
  count plus whether headings are themselves links to other pages (a
  "latest news"/live-updates page); the URL's own shape (`/category/`,
  `/tag/`, `/author/`, ...); and a repeated-identical-class "card grid"
  structure (component-grid sites - React/Next.js card layouts - render
  every teaser as a styled `<div>` with no heading tags and no real
  `<a href>` at all, navigation happens via a JS onClick handler that
  never appears in the static HTML this provider fetches, so neither of
  the other two checks can see the pattern; N+ elements sharing an exact
  tag+class combination, each holding a teaser-sized chunk of text, is
  what gives it away instead)
- Extract text at block-level granularity (`<p>`, `<li>`, `<h1-6>`, ...),
  not per-tag: the previous per-tag `get_text("\n")` split inserted a line
  break between *any* two tags, including an inline one naming an entity
  mid-sentence (e.g. "...um Comitê Gestor, denominado <strong>Comitê do
  Rio Doce</strong>, ao qual compete...") - fragmenting one sentence into
  three separate "lines" and corrupting both keyword-match excerpts and
  the summary built from them, on top of producing far more visual line
  breaks than the source page actually has. `<br>` is still honored as an
  intentional line break within a block (common in WYSIWYG-authored
  content, e.g. a bold section label followed by `<br>` then the real
  paragraph, both inside one `<p>`).
- Filter known non-article-prose lines by pattern: nav/share/comment
  boilerplate, copyright/tagline footers, an audio-player widget's own
  caption and the browser's `<audio>` fallback text, and byline/date/
  reading-time metadata ("Publicado em ...", "Atualizado em ...", "X min
  de leitura")
- Extract publication date when available
- Generate Publication objects, one per accepted link

`max_pages` (default 60, overridable per source via `source.config`) is a
safety cap on how many candidate pages get downloaded per run - not a
relevance filter. Relevance/recency narrowing is the Pipeline's date filter
(`Pipeline.filter_by_date`), applied after collection.

Current limitation:

Each monitored HTML page generates one Publication - a single page listing
multiple articles (other than the listing pages already filtered out above)
isn't split into several Publications.

Known gap: sites that render their content client-side via JavaScript
return an essentially empty `<body>` to a plain HTTP GET, so this provider
extracts nothing from them (confirmed on a handful of sources, e.g. Atlas
Público, Jornal Minas Gerais, Nexo Jornal). Fixing this would require a
headless-browser-based provider (Playwright/Selenium).

---

# Publication

Publication is the central entity of the monitoring engine.

Every Provider converts its data into this object.

Current attributes:

- id
- title
- content
- source_id
- source_name
- url
- publication_date
- author
- category
- metadata

`category` is populated from the page's own metadata when a Provider can
extract one (e.g. an `article:section` meta tag), falling back to the
originating Source's configured `category` otherwise. Both the RSS and HTML
Providers apply this fallback.

---

# Processors

Processors analyze Publications.

Providers never search keywords.

Outputs never analyze data.

Each Processor has one responsibility.

---

## Keyword Processor

Implemented.

Responsibilities:

- Search selected keywords
- Generate excerpts
- Return Result objects

Each keyword occurrence generates a Result - so a Publication mentioning
the same keyword in several paragraphs produces several `keyword`-type
Results for that one Publication. Consumers that display results per
publication (Results tab, Clipping, CSV export) use
`ProcessedPublication.keyword_results()` to collapse those down to one
representative Result per distinct keyword, rather than showing the same
publication repeated once per paragraph match.

Current keywords are plain strings (`keywords.json` is a flat list) with no
category or "how broad is this term" distinction - see Roadmap for a noted
idea to change that.

---

## Summary Processor

Implemented.

Current implementation uses an extractive approach.

Steps:

1. Drop lines that are a known non-summary marker (a standardized
   accessibility image-description caption, "PARA TODOS VEREM: ...") or a
   short, fully-uppercase heading/menu label ("APRESENTAÇÃO") - kept in
   `publication.content` itself (an image-only post can have nothing else
   substantial on the page), excluded only from summary-sentence
   selection. Only fully-uppercase short lines are dropped, not any
   short/unpunctuated line - a mixed-case fragment like "Comitê do Rio
   Doce" can just as easily be the tail of a real sentence (get_text
   inserts a boundary around inline tags too) as it can be a label, and
   dropping those corrupted the sentence around them instead of cleaning
   it up.
2. Split the remaining content into sentences
3. Ignore short sentences
4. Select the first relevant sentences
5. Generate a summary

Current implementation is intentionally simple.

An Ollama-based (local LLM) alternative was prototyped and evaluated as a
straight comparison against this extractive approach - see Known
Limitations for why it wasn't adopted. Future versions may still pursue
AI-generated summaries, but not via that specific prototype as-is.

---

# Result

Each processor returns one or more Result objects.

Example:

```python
Result(
    publication_id="...",
    processor="keyword",
    type="keyword",
    value="Rio Doce",
    metadata={}
)
```

Examples of Result types:

- keyword
- summary
- regex
- sentiment
- classification
- entity

---

# ProcessedPublication

Represents the complete processing of one Publication.

Contains:

- Original Publication
- All generated Results
- Metadata

```
Publication
      │
      ▼

ProcessedPublication

      │

 ┌────┴────┐

 ▼         ▼

Keyword   Summary
```

---

# Outputs

Outputs export processed information.

Implemented:

## CSV

Exports monitoring results.

Generated file:

```
output/results.csv
```

---

## JSON

Exports complete processed structures.

Generated file:

```
output/results.json
```

---

Future outputs:

- PostgreSQL
- SQLite
- Excel
- ElasticSearch

---

# Clipping

The application includes a clipping generation module.

Current features:

- WhatsApp-friendly formatting
- Category grouping
- Source identification
- Link generation
- Summary display
- Clipboard copy
- TXT export

Category grouping uses the matched keyword's own category when configured,
falling back to the Publication's category (which itself falls back to the
Source's category - see Sources/Publication above) when the keyword has
none. Since `keywords.json` currently has no per-keyword categories, every
clipping section header today is effectively driven by Source category.

Implemented in four places kept in sync: `legacy/interface/tabs/clipping.py`
(Tkinter), `interface_qt/clipping_tab.py` (PySide6), `outputs/whatsapp.py`
(the `Output` used by a headless/CLI run), and `interface_web/app.py`'s
`/clipping` route (web).

Example:

```
📌 Clipping – Radar Gualaxo

📅 31/07/2026

📌 Rio Doce

• Publication title

   o Source: G1

   o Link:
   https://...

   o Summary:
   ...
```

---

# Processing Pipeline

Current execution flow:

```
Source

   │

   ▼

Provider

   │

   ▼

Publication

   │

   ├─────────────┐
   ▼             ▼

Keyword      Summary

   │             │

   └──────┬──────┘

          ▼

ProcessedPublication

          │

     ┌────┴────┐

     ▼         ▼

   CSV       JSON
```

`Pipeline.filter_by_date` runs right after `Provider.collect`, before
Processors, whenever the UI has a period selected (24h / 7 days / 30 days /
custom range - there's currently no "no filter" option). A Publication
with no extractable `publication_date` is always kept: most institutional/
government sources expose no machine-readable publish date at all, and
silently dropping their content whenever a period filter is active -
regardless of keyword relevance - defeated the point of monitoring them.
The date filter narrows down publications it *can* place in time; it isn't
a relevance filter.

---

# Project Structure

```
c_monitor/

│
├── main.py                      (still launches interface_qt/ - the PySide6
│                                  desktop app - by default; see Web Application)
├── README.md
├── requirements.txt
├── config.txt                   (deployment instructions for a new machine)
├── claude_config.txt            (Claude Code setup notes for a new machine)
│
├── config/
│   ├── json_storage.py
│   ├── keywords.py
│   ├── sources.py
│   ├── schedule.py
│   └── data/
│       ├── keywords.json
│       ├── sources.json
│       └── schedule.json
│
├── core/
│   ├── publication.py
│   ├── source.py
│   ├── provider.py
│   ├── processor.py
│   ├── output.py
│   ├── result.py
│   ├── processed_publication.py
│   └── pipeline.py
│
├── providers/
│   ├── rss/
│   │   └── provider.py
│   └── html/
│       ├── provider.py
│       ├── discovery.py
│       ├── filters.py
│       ├── cleaners.py
│       └── extractor.py
│
├── processors/
│   ├── keyword.py
│   └── summary.py
│
├── outputs/
│   ├── csv.py
│   ├── json.py
│   └── whatsapp.py
│
├── interface_qt/                (PySide6 - main.py's default entry point)
│   ├── app.py
│   ├── main_window.py
│   ├── theme.py
│   ├── widgets.py
│   ├── source_dialog.py
│   ├── monitoring_controller.py
│   ├── monitoring_worker.py
│   ├── configuration_tab.py
│   ├── results_tab.py
│   ├── clipping_tab.py
│   └── logs_tab.py
│
├── interface_web/                (Flask - v1's primary interface, run explicitly
│   │                              via `python -m interface_web.app`)
│   ├── app.py
│   ├── templates/
│   │   └── index.html
│   └── static/
│       ├── app.js
│       └── style.css
│
├── wppsender/                    (standalone Selenium tool, not wired to the
│   │                              Pipeline/interfaces - run manually)
│   ├── send_clipping.py          (rebuilds the clipping text from
│   │                              output/results.json, sends it to one
│   │                              specific WhatsApp group)
│   └── requirements.txt          (selenium, pyperclip - separate from the
│                                  main app's requirements.txt)
│
├── legacy/                       (not wired into the app, not imported by
│   │                              anything outside itself - kept for
│   │                              rollback/reference only)
│   ├── interface/                (original Tkinter desktop app)
│   │   ├── app.py
│   │   ├── main_window.py
│   │   ├── menu.py
│   │   ├── statusbar.py
│   │   ├── source_dialog.py
│   │   ├── controllers/
│   │   │   └── monitoring_controller.py
│   │   └── tabs/
│   │       ├── configuration.py
│   │       ├── results.py
│   │       ├── clipping.py
│   │       └── logs.py
│   ├── prototypes/               (throwaway UI comparisons, never wired to the app)
│   │   ├── sample_data.py
│   │   ├── results_customtkinter.py
│   │   └── results_pyside6.py
│   └── wppsender_old/            (older, unrelated mass-send automation -
│       ├── main.py                kept but not used by wppsender/send_clipping.py)
│       └── envio_funcoes.py
│
├── comparative.txt              (extraction/keyword-matching validation log
│                                  against real-world reference clippings)
│
├── output/
│
├── logs/
│
└── temp/
```

---

# Design Principles

The project follows:

- SOLID principles
- Single Responsibility Principle
- Open/Closed Principle
- Low coupling
- High cohesion
- Composition over inheritance
- Domain First Architecture
- Provider-based Architecture

The core pipeline should never need modification when adding new Providers.

---

# Development Status

## Completed

- Domain entities
- Pipeline orchestration
- RSS Provider
- HTML Provider, including:
  - Same-domain, same-section-prioritized link discovery
  - Article vs. listing/hub page classification (heading density +
    whether headings link elsewhere), correcting for page-builder sites
    that reuse the same selector for real articles and teaser cards
  - `max_pages` as a per-source-overridable safety cap rather than a
    relevance filter
- Keyword Processor
- Summary Processor
- CSV Output
- JSON Output
- WhatsApp clipping Output
- Tkinter desktop interface (`legacy/interface/`) - kept as fallback, no
  longer the default entry point
- PySide6 desktop interface (`interface_qt/`) - now the default entry
  point; Results, Configuration, Logs and Clipping tabs implemented and
  wired to the real Pipeline, with a background-thread pipeline run and a
  status-bar progress bar
- Source management (including per-source `max_pages` override and,
  in the PySide6 interface, per-run source selection)
- Keyword management
- Monitoring execution
- `Pipeline.filter_by_date` includes (rather than excludes) publications
  with no extractable `publication_date`, since most institutional/
  government sources expose none
- `Pipeline.run()` accepts an optional `on_progress(current, total)`
  callback, decoupling progress reporting from any particular interface
- Clipping generation, with category inheritance from Source → Publication
  → Result and de-duplication of repeated keyword matches within one
  publication (`ProcessedPublication.keyword_results()`)
- 73 curated sources in `sources.json`, validated against four real-world
  reference clippings (see `comparative.txt`)
- Flask web interface (`interface_web/`) - Busca/Resultados/Clipping/
  Configuração tabs, session-scoped background job execution, source and
  keyword CRUD, a persisted (not yet executed) background-run schedule
  setting - see Web Application above
- HTML extraction quality: block-level text extraction (fixed sentence
  fragmentation), `<body>`/`<html>`-resolving-selector rejection, repeated
  card-grid listing detection, audio-widget/byline-metadata line filtering
  - see HTML Provider above
- Summary quality: accessibility-caption and all-caps-label filtering
  without corrupting inline mid-sentence fragments - see Summary Processor
  above
- Rebrand from "C-Monitor" to "Radar Gualaxo" across every interface,
  output and doc
- An Ollama-based (local LLM) summarizer was prototyped and compared
  against the extractive Summary Processor - not adopted, see Known
  Limitations
- Querido Diário's public API and the DOU/`in.gov.br` ecosystem were
  evaluated for official-gazette coverage - neither integrated yet, see
  Known Limitations and the Version 2 government/gazette integrations
  entry in Roadmap
- Orquestração split into its own tab, with its own keyword/source
  selection independent from the Busca tab's, persisted to
  `config/data/schedule.json` (`config/schedule.py`) - see Web
  Application above
- `wppsender/send_clipping.py` - a standalone Selenium script (not part
  of the Pipeline/interfaces) that rebuilds the clipping text from
  `output/results.json` and sends it to one specific WhatsApp group by
  pasting into WhatsApp Web's own compose box, reusing the browser-
  automation mechanics from an older, unrelated mass-send tool, moved to
  `legacy/wppsender_old/` (`main.py`, `envio_funcoes.py` - Postgres
  registration, DOCX report generation, per-contact batching, none of
  which `send_clipping.py` needs or uses)
- A "📲 Enviar pro WhatsApp" button on the web Clipping tab
  (confirm-gated) writes the currently-shown clipping text to
  `output/clipping_to_send.txt` and fires
  `wppsender/send_clipping.py --file ...` as a background subprocess
- Orquestração now actually executes: an in-process `APScheduler`
  `BackgroundScheduler` in `interface_web/app.py` reads
  `config/data/schedule.json` and runs the Pipeline unattended on the
  configured interval, rescheduling immediately whenever the Orquestração
  form is saved - see Web Application above
- "Período específico" (explicit start/end dates) added as a period
  option in both Busca and Orquestração, alongside 24h/7 dias/30 dias
- `Publication.is_static_reference` - a new field, populated by the
  HTML Provider via `providers/html/filters.looks_like_static_reference`
  (URL-shape based, e.g. `.../governanca`, `.../perguntas-frequentes` -
  deliberately excludes the too-broad `.../transparencia` after it
  falsely flagged a real dated edital living under that same site
  section). `Pipeline.filter_by_date` now excludes an undated
  publication flagged this way once a specific period is requested,
  instead of always including it like a genuinely-undated news item -
  fixes static BNDES FAQ/overview pages resurfacing regardless of the
  date range searched
- `HTMLProvider._extract_publication_date` gained a text-based fallback
  (`_extract_date_from_text`) for pages with no `<meta>`/`<time>` date
  at all but that state their own publish/launch date in visible text
  (e.g. an edital's "Lançamento do edital: 26 de julho de 2024") - only
  lines naming a publish-indicating trigger word are checked, so an
  unrelated date elsewhere in the body isn't mistaken for the page's own
  date. Confirmed fixing a 2024 Fundo Brasil edital that kept appearing
  in every search regardless of period because its only date lived in
  body text, not metadata
- `STATIC_REFERENCE_URL_MARKERS` gained `"ferramentas-ministerios"`
  (another BNDES Fundo Rio Doce reference page, same class as
  governança/perguntas-frequentes above)
- `ContentExtractor.STRONG_SELECTORS` gained `.tdb_single_content`/
  `.td-post-content` (tagDiv's "Newspaper" WordPress theme's dedicated
  post-content class), and `_longest_match` now excludes any candidate
  carrying a `tdb_templates` class. That theme builds an entire
  single-post *page* - breadcrumbs, sidebar "trending headlines" widget,
  "Mais Lidas" widget, and the real post - as one WPBakery-composed
  layout definition wrapped in `<article class="tdb_templates">`, so a
  plain `article` match is *always* longer than the theme's own content
  selector (it structurally contains that content plus everything
  else) - "longest wins" alone always picked the wrapper. Confirmed on
  seculodiario.com.br: a sidebar "trending headlines" list that
  happened to mention "Novo Acordo do Rio Doce" was producing a false
  keyword match on unrelated articles purely by proximity, not because
  the article itself was actually about the Rio Doce agreement

## Known Limitations

- Orquestração's `APScheduler` only fires while the Flask process
  (`python -m interface_web.app`) is actually running on that machine -
  deliberate choice for now (the user monitors that machine directly), no
  OS-level scheduler (Windows Task Scheduler, a service wrapper like
  NSSM) involved to auto-restart the process itself if it crashes or the
  machine reboots. If the process goes down, orchestrated runs simply
  stop until someone starts it again - nothing queues up or catches up
  retroactively.
- Sites that render content via JavaScript aren't readable by the HTML
  Provider (confirmed: Atlas Público, Jornal Minas Gerais, Nexo Jornal) -
  needs a headless-browser-based provider
- The HTML Provider's link discovery only looks at whatever's linked from
  a source's page at the moment a run happens - an article that's already
  scrolled off by then is invisible to it regardless of whether it's
  inside the requested date range or would extract cleanly. Confirmed
  empirically: of 20 real-world reference-clipping URLs, 10 misses traced
  to exactly this (verified individually - each extracted cleanly and
  passed the date filter once fetched directly). RSS was substituted for
  8 high-volume sources as a partial mitigation (see Sources above), but
  the only complete fix is running frequently enough that nothing scrolls
  off between runs - the Orquestração tab's APScheduler-backed runs (see
  Web Application) now provide that, as long as the process stays up
- `output/results.json` and `config/data/*.json` are unlocked,
  last-writer-wins targets shared across web sessions - acceptable for
  now since `output/results.json` is a validation-only artifact for this
  stage (Postgres, with row-matching dedup against what's already stored,
  is the planned durable store - see Roadmap), and concurrent config edits
  are an edge case at this stage's usage level
- The Ollama-based summarizer prototype (llama3.2:3b, local) produced
  noticeably more coherent summaries than the extractive approach and
  could surface the actually-relevant fact even when it wasn't in the
  first two sentences - but fabricated a specific, plausible-looking
  statistic in 1 of 3 spot-checked cases (a "mais de 1.000 pessoas"
  headcount that appears nowhere in the source text). For a project
  whose output describes a reparations process, an unverified invented
  number is a worse failure mode than a duller but grounded extractive
  summary - not adopted as-is. A prompt instructing the model to omit all
  figures/dates/statistics was proposed as a mitigation but not tested
  against a larger sample before deciding to defer this
- Querido Diário's public API (`api.queridodiario.ok.org.br`) is
  municipal-gazette-only (indexed by IBGE territory code) - confirmed via
  live queries that it does not cover any Rio Doce basin municipality
  relevant to this project (Mariana, Governador Valadares, Colatina,
  Ipatinga, Barra Longa, Belo Oriente all returned zero indexed gazettes),
  and by design it never covers the DOU (federal) at all
- `in.gov.br/consulta` (the DOU's own search) returned HTTP 403 on both a
  direct request and a fetch-tool request during evaluation, consistent
  with active bot/WAF protection specifically on that search subsystem
  (other `in.gov.br` pages already work fine with this project's plain
  `requests`-based HTMLProvider) - scraping it directly would likely need
  real browser automation, not a simple HTTP GET. INLabs
  (`inlabs.in.gov.br`), the Imprensa Nacional's own open-data portal, was
  identified as the legitimate path instead - free registration, daily
  full-text XML dumps of the DOU - but isn't implemented; it would need a
  new Provider shape (login + daily-dump download + XML parse) rather
  than reusing the HTML/RSS Provider pattern as-is
- `KeywordProcessor` does pure lexical matching with no notion of which
  keywords are unambiguous "anchor" terms (e.g. "Rio Doce", "Mariana")
  versus broad "context" terms (e.g. "Vale", "Brasil") that are only
  meaningful alongside an anchor term - a generic keyword added on its own
  will currently match unrelated content
- `keywords.json` has no per-keyword category, so Clipping section headers
  are effectively driven entirely by Source category today (see Clipping
  above) - a category↔keyword mapping table has been suggested as a future
  improvement, letting a keyword either declare its own category or inherit
  one from a shared table instead of only from the Source
- Some sources derived from a single reference article (rather than
  configured by hand) resolve to a broad/generic section of that outlet
  (e.g. a domain root or a national "brasil"/"geral" section) whose
  assigned category reflects only the one article originally tested, not
  necessarily everything that section will publish going forward

---

# Roadmap

## Version 1

- Desktop application (Tkinter, then PySide6)
- Web application (Flask) - added this cycle as v1's primary interface,
  see Web Application
- RSS Provider
- HTML Provider
- Keyword Processor
- Summary Processor
- JSON Output
- CSV Output
- Clipping module

v1 is intentionally still on JSON storage - `output/results.json` and
`config/data/*.json` are validation-stage artifacts, not meant to be
concurrency-hardened (see Known Limitations). Postgres, with dedup by
matching an incoming row against what's already stored, is planned for a
later version rather than retrofitted onto the JSON files.

---

## Version 2

- Search Provider
- Sitemap Provider
- Better HTML extraction - substantially done (see HTML Provider); still
  missing: headless-browser rendering for JavaScript-only sites, and
  multiple-articles-per-page support
- Website-specific parsers
- Duplicate detection - done at two levels: `Pipeline.run()` skips a
  Publication whose `content_hash()` (title+content, deliberately
  excluding URL so the same article reached via two different tracked
  URLs still collapses) was already seen earlier in the same run; within
  one Publication, repeated same-keyword matches across paragraphs
  collapse to one representative Result (`keyword_results()`)
- PySide6 desktop interface - not originally planned, added this cycle as
  a modernization of `interface/` and now the default entry point (see
  Desktop Application) - done
- Date filter includes, rather than excludes, Publications with no
  extractable date - done (see Processing Pipeline)
- Keyword categorization: distinguish anchor vs. context keywords, and/or
  a category↔keyword mapping table, so Clipping grouping and relevance
  matching don't depend solely on Source category (see Known Limitations)
- PDF Provider
- API Provider
- Government/official-gazette integrations (same sphere as API Provider
  above):
  - Querido Diário API - evaluated: municipal-gazette-only, confirmed to
    have zero coverage of the Rio Doce basin municipalities this project
    needs, and out of scope for DOU by design (see Known Limitations).
    Could still be worth revisiting for other, already-covered
    municipalities if the project's scope broadens
  - DOU / `in.gov.br` - evaluated: the public search
    (`in.gov.br/consulta`) is bot-protected; INLabs
    (`inlabs.in.gov.br`) is the identified legitimate path (free
    registration, daily full-text XML) but needs a new Provider shape
    (see Known Limitations)
  - Municipal diários oficiais for the specific Rio Doce basin cities not
    covered by Querido Diário - not yet investigated; likely means
    per-municipality HTML sources (same pattern as every other source
    today) or a shared state-level consortium platform if one covers
    multiple relevant cities at once

---

## Version 3

- PostgreSQL Output
- Scheduling - in-process (`APScheduler`) done this cycle, ahead of
  schedule (see Web Application / Development Status); an OS-level
  layer (auto-restart the process itself) is the still-open part, if
  ever needed - not planned unless the "one person monitors the
  machine directly" assumption stops holding
- Incremental monitoring
- AI Summaries
- AI Classification
- Entity Recognition
- Sentiment Analysis
- Similar publication detection
- Vector databases (supporting AI providers/similar-publication detection
  above)

---

# Long-Term Goal

Transform Radar Gualaxo into a generic monitoring platform capable of collecting information from heterogeneous sources while keeping collection, processing and storage completely independent.

The architecture is designed so that implementing a new Provider requires only a new class implementing the Provider contract.

No changes to the Pipeline should be necessary.

This allows the platform to continuously evolve without architectural rewrites.