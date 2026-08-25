"""
interface_qt/clipping_tab.py

Clipping tab, rebuilt in PySide6. Same set_results(results) contract
as the Tkinter version (interface/tabs/clipping.py).

Uses ProcessedPublication.keyword_results() (see core/processed_publication.py)
so a publication with several paragraph-level keyword matches shows up
once in the clipping, not once per matched paragraph.
"""

from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDateEdit, QPushButton,
    QTextEdit, QFileDialog, QMessageBox,
)

from interface_qt.widgets import Card


class ClippingTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.results = []

        self._build_ui()

    # ------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        toolbar.addWidget(QLabel("Período:"))

        self.period_date = QDateEdit(calendarPopup=True)
        self.period_date.setDisplayFormat("dd/MM/yyyy")
        self.period_date.setDate(QDate.currentDate())
        toolbar.addWidget(self.period_date)

        toolbar.addStretch()

        generate_btn = QPushButton("Gerar Clipping")
        generate_btn.setObjectName("primaryButton")
        generate_btn.clicked.connect(self.generate)
        toolbar.addWidget(generate_btn)

        copy_btn = QPushButton("Copiar WhatsApp")
        copy_btn.clicked.connect(self.copy_clipboard)
        toolbar.addWidget(copy_btn)

        export_btn = QPushButton("Exportar TXT")
        export_btn.clicked.connect(self.export_txt)
        toolbar.addWidget(export_btn)

        layout.addLayout(toolbar)

        card = Card("Prévia")
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        card.body.addWidget(self.preview)
        layout.addWidget(card, stretch=1)

    # ------------------------------------------------------------
    # Public API (mirrors interface/tabs/clipping.py)
    # ------------------------------------------------------------

    def set_results(self, results) -> None:
        self.results = results

    # ------------------------------------------------------------

    def generate(self):
        if not self.results:
            QMessageBox.warning(self, "Clipping", "Nenhum resultado disponível.")
            return

        self.preview.setPlainText(self._build_clipping())

    # ------------------------------------------------------------

    def _build_clipping(self) -> str:
        lines = [
            "📌 *Clipping – Radar Gualaxo*",
            f"📅 *{self.period_date.date().toString('dd/MM/yyyy')}*",
            "",
        ]

        categories: dict[str, dict] = {}

        for processed in self.results:
            publication = processed.publication

            summary = ""
            for result in processed.results:
                if result.type == "summary":
                    summary = result.value

            for result in processed.keyword_results():
                category = (
                    result.metadata.get("category")
                    or publication.category
                    or "Outros Temas"
                )
                emoji = result.metadata.get("emoji", "📌")

                bucket = categories.setdefault(
                    category, {"emoji": emoji, "items": []}
                )
                bucket["items"].append({
                    "title": publication.title,
                    "source": publication.source_name,
                    "url": publication.url,
                    "summary": summary,
                })

        for category, data in categories.items():
            lines.append(f"{data['emoji']} *{category}*")
            lines.append("")

            for item in data["items"]:
                lines.append(f"• {item['title']}")
                lines.append(f"   o Veículo: {item['source']}")
                lines.append(f"   o Link: {item['url']}")
                if item["summary"]:
                    lines.append(f"   o Resumo: {item['summary']}")
                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------

    def copy_clipboard(self):
        QGuiApplication.clipboard().setText(self.preview.toPlainText())
        QMessageBox.information(self, "WhatsApp", "Clipping copiado.")

    # ------------------------------------------------------------

    def export_txt(self):
        text = self.preview.toPlainText()

        if not text.strip():
            QMessageBox.warning(self, "Exportar", "Gere o clipping primeiro.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar clipping", "clipping.txt", "Arquivo texto (*.txt)"
        )

        if not path:
            return

        with open(path, "w", encoding="utf-8") as file:
            file.write(text)

        QMessageBox.information(self, "Exportar", "Arquivo salvo.")
