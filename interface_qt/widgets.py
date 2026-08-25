"""
interface_qt/widgets.py

Small shared widgets used across tabs, so every "section" in the app
(Sources, Keywords, Search Period, Logs, Clipping preview...) looks
like a consistent rounded white card instead of each tab inventing its
own container.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel


class Card(QFrame):
    """
    A titled, rounded, white container. Use `.body` as the layout to
    add content into.
    """

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self.setObjectName("card")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 14, 16, 16)
        outer.setSpacing(10)

        if title:
            title_label = QLabel(title)
            title_label.setObjectName("cardTitle")
            outer.addWidget(title_label)

        self.body = QVBoxLayout()
        self.body.setSpacing(8)
        outer.addLayout(self.body, stretch=1)
