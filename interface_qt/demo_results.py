"""
interface_qt/demo_results.py

Runs the REAL pipeline (HTMLProvider + KeywordProcessor, real
keywords.json) against the Itatiaia source and feeds the actual
ProcessedPublication results into the PySide6 ResultsTab - proving the
widget works with real data, not the prototype's sample rows.

The window opens immediately with the empty state, then fills in once
the (synchronous, network-bound) pipeline run finishes - the same
blocking behavior the current Tkinter app has today (MonitoringController
runs the pipeline on the UI thread too). Moving this to a background
thread is a improvement for a later step, not this one.

Run from the project root: python -m interface_qt.demo_results
"""

import sys

from PySide6.QtWidgets import QApplication, QMainWindow

from config.keywords import load_keywords
from core.pipeline import Pipeline
from core.source import Source
from processors.keyword import KeywordProcessor
from providers.html.provider import HTMLProvider
from providers.rss.provider import RSSProvider

from interface_qt.results_tab import ResultsTab
from interface_qt.theme import STYLESHEET


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    window = QMainWindow()
    window.setWindowTitle("Radar Gualaxo — Resultados (PySide6, dados reais)")
    window.resize(1100, 640)

    results_tab = ResultsTab()
    window.setCentralWidget(results_tab)
    window.show()

    app.processEvents()  # paint the empty state before the blocking run below

    keywords = load_keywords()

    source = Source(
        name="Itatiaia",
        provider="html",
        url="https://www.itatiaia.com.br/valedoaco/",
    )

    pipeline = Pipeline(
        providers={
            "html": HTMLProvider(),
            "rss": RSSProvider(),
        },
        processors=[KeywordProcessor(keywords)],
        outputs=[],
    )

    processed = pipeline.run([source])

    results_tab.show_results(processed)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
