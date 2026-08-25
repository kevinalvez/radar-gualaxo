"""
interface_qt/source_dialog.py

Add/edit Source dialog, rebuilt in PySide6.

Unlike the Tkinter version (interface/source_dialog.py), editing a
source preserves its current "enabled" state instead of silently
forcing it back to True - and exposes an explicit checkbox for it, so
disabling a broken source doesn't quietly get undone next time
someone edits it.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QCheckBox, QPushButton, QHBoxLayout,
)

PROVIDERS = ["rss", "html", "sitemap", "api", "search", "pdf"]


class SourceDialog(QDialog):

    def __init__(self, parent=None, source: dict | None = None):
        super().__init__(parent)

        self.setWindowTitle("Fonte")
        self.setMinimumWidth(420)

        self.source = source
        self.result: dict | None = None

        self._build_ui()

        if source:
            self._load_source(source)
        else:
            self.enabled_checkbox.setChecked(True)

    # ------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)

        self.name_field = QLineEdit()
        form.addRow("Nome:", self.name_field)

        self.provider_field = QComboBox()
        self.provider_field.addItems(PROVIDERS)
        form.addRow("Provider:", self.provider_field)

        self.url_field = QLineEdit()
        form.addRow("URL:", self.url_field)

        self.category_field = QLineEdit()
        form.addRow("Categoria:", self.category_field)

        self.description_field = QLineEdit()
        form.addRow("Descrição:", self.description_field)

        self.enabled_checkbox = QCheckBox("Habilitada")
        form.addRow("", self.enabled_checkbox)

        layout.addLayout(form)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_button = QPushButton("Cancelar")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)

        save_button = QPushButton("Salvar")
        save_button.setObjectName("primaryButton")
        save_button.clicked.connect(self._save)
        buttons.addWidget(save_button)

        layout.addLayout(buttons)

    # ------------------------------------------------------------

    def _load_source(self, source: dict):
        self.name_field.setText(source.get("name", ""))

        provider = source.get("provider", "rss")
        index = self.provider_field.findText(provider)
        self.provider_field.setCurrentIndex(index if index >= 0 else 0)

        self.url_field.setText(source.get("url", ""))
        self.category_field.setText(source.get("category") or "")
        self.description_field.setText(source.get("description") or "")
        self.enabled_checkbox.setChecked(source.get("enabled", True))

    # ------------------------------------------------------------

    def _save(self):
        self.result = {
            "name": self.name_field.text().strip(),
            "provider": self.provider_field.currentText(),
            "url": self.url_field.text().strip(),
            "enabled": self.enabled_checkbox.isChecked(),
            "category": self.category_field.text().strip(),
            "description": self.description_field.text().strip(),
        }
        self.accept()
