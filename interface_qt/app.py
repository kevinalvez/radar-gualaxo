"""
interface_qt/app.py

Entry point for the PySide6 interface. Mirrors interface/app.py::start().

Run from the project root: python -m interface_qt.app
"""

import sys

from PySide6.QtWidgets import QApplication

from interface_qt.main_window import MainWindow
from interface_qt.theme import STYLESHEET


def start():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    window = MainWindow()
    window.show()

    app.exec()

    return window


if __name__ == "__main__":
    start()
