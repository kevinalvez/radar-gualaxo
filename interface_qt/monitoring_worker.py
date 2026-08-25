"""
interface_qt/monitoring_worker.py

Runs the monitoring Pipeline on a background QThread, so the window
stays responsive while a run (network-bound, potentially several
minutes across many sources) is in progress.

Emits signals rather than touching any widget directly - Qt marshals
cross-thread signal/slot connections onto the receiving (main) thread's
event loop automatically, so connected slots (LogsTab.write, etc.) run
safely there.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class MonitoringWorker(QThread):

    log = Signal(str)
    progress = Signal(int, int)  # current, total
    finished_ok = Signal(object)  # list[ProcessedPublication]
    failed = Signal(str)

    def __init__(self, controller, keywords, period, parent=None):
        super().__init__(parent)

        self.controller = controller
        self.keywords = keywords
        self.period = period

    # ------------------------------------------------------------

    def run(self) -> None:

        try:
            sources = self.controller.build_sources()

            for source in sources:
                self.log.emit(
                    f"SOURCE => {source.name} | {source.provider} | {source.url}\n"
                )

            self.log.emit(f"Sources carregadas: {len(sources)}\n")

            pipeline = self.controller.create_pipeline(self.keywords)

            self.log.emit(
                f"Executando pipeline com {len(sources)} fontes\n"
            )

            processed = pipeline.run(
                sources,
                self.period,
                on_progress=lambda current, total: self.progress.emit(current, total),
            )

            self.log.emit(
                f"Pipeline retornou {len(processed)} publicações\n"
            )

            for item in processed:
                self.log.emit(
                    f"{item.publication.title} | "
                    f"{item.publication.publication_date} | "
                    f"resultados={len(item.results)}\n"
                )

            self.log.emit(
                f"Publicações processadas: {len(processed)}\n"
            )

            self.finished_ok.emit(processed)

        except Exception as error:
            self.failed.emit(str(error))
