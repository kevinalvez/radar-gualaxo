"""
prototypes/results_pyside6.py

Prototype: Results tab rebuilt with PySide6 (Qt).

Uses a real QTableView backed by QStandardItemModel, with a
QSortFilterProxyModel wired to the search box - clicking a column
header sorts the table, and typing filters rows, both built into Qt
rather than hand-rolled.

Run: python prototypes/results_pyside6.py
"""

import sys

from PySide6.QtCore import Qt, QSortFilterProxyModel
from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QTableView, QLabel, QHeaderView,
)

from sample_data import ROWS

COLUMNS = ("Fonte", "Título", "Keyword", "Excerto")


class ResultsPrototype(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Radar Gualaxo — Protótipo Resultados (PySide6)")
        self.resize(1100, 600)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        layout.addLayout(self._build_toolbar())
        layout.addWidget(self._build_table())

    # ------------------------------------------------------------

    def _build_toolbar(self):
        toolbar = QHBoxLayout()

        toolbar.addWidget(QLabel("Buscar:"))

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "filtrar por título, fonte ou keyword..."
        )
        self.search_box.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_box)

        toolbar.addStretch()

        export_button = QPushButton("Exportar CSV")
        toolbar.addWidget(export_button)

        return toolbar

    # ------------------------------------------------------------

    def _build_table(self):
        self.model = QStandardItemModel(0, len(COLUMNS))
        self.model.setHorizontalHeaderLabels(COLUMNS)

        for row in ROWS:
            items = [QStandardItem(str(value)) for value in row]
            for item in items:
                item.setEditable(False)
            self.model.appendRow(items)

        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy.setFilterKeyColumn(-1)  # search across all columns

        self.table = QTableView()
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.Stretch
        )
        self.table.verticalHeader().setVisible(False)

        return self.table

    # ------------------------------------------------------------

    def _apply_filter(self, text):
        self.proxy.setFilterFixedString(text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ResultsPrototype()
    window.show()
    sys.exit(app.exec())
