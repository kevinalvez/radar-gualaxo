"""
interface_qt/monitoring_controller.py

Same responsibility as interface/controllers/monitoring_controller.py:
glue between the UI tabs and the core Pipeline. Kept as a separate
copy (rather than imported) because the only Tkinter-specific line in
the original - selecting a tab via notebook.select(widget) - has a
different API in Qt (tabs.setCurrentWidget(widget)); everything else
is identical, except that the Pipeline run itself happens on a
background QThread (see monitoring_worker.py) instead of blocking the
UI thread for the duration of the run.
"""

from __future__ import annotations

from core.pipeline import Pipeline
from core.source import Source

from config.sources import load_sources

from providers.rss.provider import RSSProvider
from providers.html.provider import HTMLProvider
from processors.keyword import KeywordProcessor
from processors.summary import SummaryProcessor

from outputs.json import JsonOutput

from interface_qt.monitoring_worker import MonitoringWorker


class MonitoringController:

    def __init__(
        self,
        configuration,
        logs,
        tabs,
        results,
        clipping,
        on_progress=None,
    ):
        self.configuration = configuration
        self.logs = logs
        self.tabs = tabs
        self.results = results
        self.clipping = clipping
        self.on_progress = on_progress
        self._worker: MonitoringWorker | None = None

    # ------------------------------------------------------------

    def run_monitor(self):
        keywords = self.configuration.get_selected_keywords()
        period = self.configuration.get_selected_period()

        if not keywords:
            self.logs.write("Nenhuma keyword selecionada\n")
            return

        self.logs.write(f"Keywords: {keywords}\n")

        self.configuration.set_running(True)

        self._worker = MonitoringWorker(self, keywords, period)
        self._worker.log.connect(self.logs.write)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    # ------------------------------------------------------------

    def _on_progress(self, current, total):
        if self.on_progress:
            self.on_progress(current, total)

    # ------------------------------------------------------------

    def _on_finished(self, processed):
        self.results.show_results(processed)
        self.clipping.set_results(processed)

        self.tabs.setCurrentWidget(self.results)

        self.configuration.set_running(False)
        self._reset_progress()

    # ------------------------------------------------------------

    def _on_failed(self, message):
        self.logs.write(f"Erro: {message}\n")

        self.configuration.set_running(False)
        self._reset_progress()

    # ------------------------------------------------------------

    def _reset_progress(self):
        if self.on_progress:
            self.on_progress(0, 0)

    # ------------------------------------------------------------

    def build_sources(self):
        configured = load_sources()
        selected_names = set(self.configuration.get_selected_sources())
        sources = []

        for item in configured:
            if isinstance(item, dict):
                if not item.get("enabled", True):
                    continue
                if item.get("name") not in selected_names:
                    continue
                sources.append(Source.from_dict(item))
            else:
                if item not in selected_names:
                    continue
                sources.append(Source(name=item, provider="rss", url=item))

        return sources

    # ------------------------------------------------------------

    def create_pipeline(self, keywords):
        providers = {
            "rss": RSSProvider(),
            "html": HTMLProvider(),
        }

        processors = [
            KeywordProcessor(keywords),
            SummaryProcessor(),
        ]

        outputs = [
            JsonOutput("output/results.json"),
        ]

        return Pipeline(providers, processors, outputs)
