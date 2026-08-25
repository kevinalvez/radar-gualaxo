"""
interface_qt/logs_tab.py

Logs tab, rebuilt in PySide6. Same write(message) contract as the
Tkinter version (interface/tabs/logs.py).
"""

from __future__ import annotations

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit

from interface_qt.widgets import Card


class LogsTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)

        card = Card("Logs de execução")
        layout.addWidget(card)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Consolas", 9))
        card.body.addWidget(self.text)

    # ------------------------------------------------------------
    # Public API (mirrors interface/tabs/logs.py::LogsTab)
    # ------------------------------------------------------------

    def write(self, message: str) -> None:
        self.text.insertPlainText(message)
        self.text.verticalScrollBar().setValue(
            self.text.verticalScrollBar().maximum()
        )

    def clear(self) -> None:
        self.text.clear()
