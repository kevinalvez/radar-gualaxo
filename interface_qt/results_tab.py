"""
interface_qt/results_tab.py

Results tab, rebuilt in PySide6.

Keeps the same show_results(processed_publications) contract as the
Tkinter version (interface/tabs/results.py), so it can be dropped into
the real MainWindow / MonitoringController later without changing
their code.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel,
    QTableView, QHeaderView, QStackedWidget, QFileDialog, QMessageBox,
)

from outputs.csv import CsvOutput

COLUMNS = ("Fonte", "Título", "Keyword", "Excerto")


class ResultsTab(QWidget):
    """
    Displays keyword matches from processed publications: searchable,
    sortable table, with CSV export.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self._processed = []

        self._build_ui()
        self._show_empty()

    # ------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        layout.addLayout(self._build_toolbar())

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_table())
        self.stack.addWidget(self._build_empty_state())
        layout.addWidget(self.stack, stretch=1)

    # ------------------------------------------------------------

    def _build_toolbar(self):
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        title = QLabel("Resultados")
        title.setObjectName("sectionTitle")
        toolbar.addWidget(title)

        toolbar.addSpacing(12)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Buscar por título, fonte ou keyword..."
        )
        self.search_box.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_box, stretch=1)

        self.count_label = QLabel("0 resultados")
        self.count_label.setObjectName("countLabel")
        toolbar.addWidget(self.count_label)

        self.export_button = QPushButton("Exportar CSV")
        self.export_button.setObjectName("primaryButton")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self._export_csv)
        toolbar.addWidget(self.export_button)

        return toolbar

    # ------------------------------------------------------------

    def _build_table(self):
        self.model = QStandardItemModel(0, len(COLUMNS))
        self.model.setHorizontalHeaderLabels(COLUMNS)

        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        return self.table

    # ------------------------------------------------------------

    def _build_empty_state(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("🗂️")
        icon.setObjectName("emptyIcon")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        message = QLabel(
            "Nenhum resultado ainda.\n"
            "Execute o monitoramento para ver as matérias encontradas aqui."
        )
        message.setObjectName("emptyMessage")
        message.setAlignment(Qt.AlignCenter)
        layout.addWidget(message)

        return page

    # ------------------------------------------------------------
    # Public API (mirrors interface/tabs/results.py::ResultsTab)
    # ------------------------------------------------------------

    def show_results(self, processed_publications) -> None:
        self._processed = processed_publications

        self.model.setRowCount(0)

        for processed in processed_publications:

            publication = processed.publication

            for result in processed.keyword_results():

                items = [
                    QStandardItem(publication.source_name),
                    QStandardItem(publication.title),
                    QStandardItem(result.value),
                    QStandardItem(result.metadata.get("excerpt", "")),
                ]

                for item in items:
                    item.setEditable(False)

                self.model.appendRow(items)

        row_count = self.model.rowCount()

        self.count_label.setText(
            f"{row_count} resultado{'s' if row_count != 1 else ''}"
        )
        self.export_button.setEnabled(row_count > 0)

        self.stack.setCurrentIndex(0 if row_count > 0 else 1)

    # ------------------------------------------------------------

    def clear(self) -> None:
        self.show_results([])

    # ------------------------------------------------------------

    def _apply_filter(self, text: str) -> None:
        self.proxy.setFilterFixedString(text)

    # ------------------------------------------------------------

    def _show_empty(self) -> None:
        self.stack.setCurrentIndex(1)

    # ------------------------------------------------------------

    def _export_csv(self) -> None:
        if not self._processed:
            QMessageBox.warning(
                self, "Radar Gualaxo", "Não há resultados para exportar."
            )
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar CSV", "output/results.csv", "CSV (*.csv)"
        )

        if not path:
            return

        CsvOutput(path).export(self._processed)

        QMessageBox.information(
            self, "Radar Gualaxo", f"CSV exportado para {path}"
        )
