"""
interface_qt/main_window.py

Main window, rebuilt in PySide6. Mirrors interface/main_window.py:
a tabbed shell (Configuração, Resultados, Logs, Clipping) wired to the
same MonitoringController pattern.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QMenuBar, QMessageBox, QProgressBar,
)

from interface_qt.configuration_tab import ConfigurationTab
from interface_qt.results_tab import ResultsTab
from interface_qt.logs_tab import LogsTab
from interface_qt.clipping_tab import ClippingTab
from interface_qt.monitoring_controller import MonitoringController


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Radar Gualaxo")
        self.resize(1280, 800)

        self._build_menu()
        self._build_tabs()
        self._build_status_bar()

        self.monitor = MonitoringController(
            configuration=self.configuration,
            logs=self.logs,
            tabs=self.tabs,
            results=self.results,
            clipping=self.clipping,
            on_progress=self._set_progress,
        )

        self.configuration.set_run_command(self.monitor.run_monitor)

    # ------------------------------------------------------------

    def _build_menu(self):
        menu_bar: QMenuBar = self.menuBar()

        file_menu = menu_bar.addMenu("Arquivo")
        file_menu.addAction("Sair", self.close)

        help_menu = menu_bar.addMenu("Ajuda")
        help_menu.addAction("Sobre", self._show_about)

    def _show_about(self):
        QMessageBox.information(self, "Radar Gualaxo", "Radar Gualaxo")

    # ------------------------------------------------------------

    def _build_status_bar(self):
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(220)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)

        self.statusBar().addPermanentWidget(self.progress_bar)
        self.statusBar().showMessage("Pronto")

    def _set_progress(self, current: int, total: int) -> None:
        if total <= 0:
            self.progress_bar.setVisible(False)
            self.statusBar().showMessage("Pronto")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.statusBar().showMessage(f"Processando fonte {current} de {total}...")

    # ------------------------------------------------------------

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.configuration = ConfigurationTab()
        self.results = ResultsTab()
        self.logs = LogsTab()
        self.clipping = ClippingTab()

        self.tabs.addTab(self.configuration, "Configuração")
        self.tabs.addTab(self.results, "Resultados")
        self.tabs.addTab(self.logs, "Logs")
        self.tabs.addTab(self.clipping, "Clipping")
