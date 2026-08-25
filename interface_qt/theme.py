"""
interface_qt/theme.py

Shared visual language for the PySide6 interface: soft light palette,
rounded corners, generous spacing, calm accent color. Applied globally
via QApplication.setStyleSheet(STYLESHEET) so every widget picks it up
without per-widget styling.
"""

# Palette
BACKGROUND = "#F7F8FA"
SURFACE = "#FFFFFF"
BORDER = "#E4E7EB"
BORDER_STRONG = "#D7DBE0"
TEXT = "#1F2933"
TEXT_MUTED = "#616E7C"
TEXT_FAINT = "#9AA5B1"
ACCENT = "#2F6FED"
ACCENT_HOVER = "#2557C7"
ACCENT_SOFT = "#E4ECFF"
DISABLED_BG = "#C1C7CD"
DISABLED_TEXT = "#F0F1F3"

STYLESHEET = f"""
* {{
    font-family: "Segoe UI", sans-serif;
    font-size: 10.5pt;
    color: {TEXT};
}}

QWidget {{
    background-color: {BACKGROUND};
}}

QMainWindow {{
    background-color: {BACKGROUND};
}}

/* ---- Toolbar / labels ---- */

QLabel#sectionTitle {{
    font-size: 13pt;
    font-weight: 600;
    color: {TEXT};
}}

QLabel#countLabel {{
    color: {TEXT_MUTED};
    padding: 0 8px;
}}

/* ---- Inputs ---- */

QLineEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: {ACCENT_SOFT};
}}

QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}

/* ---- Buttons ---- */

QPushButton {{
    background-color: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 8px;
    padding: 8px 16px;
    color: {TEXT};
}}

QPushButton:hover {{
    background-color: {ACCENT_SOFT};
    border: 1px solid {ACCENT};
}}

QPushButton#primaryButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    font-weight: 600;
}}

QPushButton#primaryButton:hover {{
    background-color: {ACCENT_HOVER};
}}

QPushButton:disabled {{
    background-color: {DISABLED_BG};
    color: {DISABLED_TEXT};
    border: none;
}}

/* ---- Table ---- */

QTableView {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    gridline-color: {BACKGROUND};
    selection-background-color: {ACCENT_SOFT};
    selection-color: {TEXT};
    alternate-background-color: #FBFCFD;
}}

QHeaderView::section {{
    background-color: #F1F3F5;
    color: #3E4C59;
    padding: 8px;
    border: none;
    border-bottom: 1px solid {BORDER};
    font-weight: 600;
}}

QTableView::item {{
    padding: 6px;
}}

/* ---- Empty state ---- */

QLabel#emptyIcon {{
    font-size: 40pt;
    color: {TEXT_FAINT};
}}

QLabel#emptyMessage {{
    color: {TEXT_MUTED};
    font-size: 11pt;
    padding-top: 4px;
}}

/* ---- Tabs (for when MainWindow adopts QTabWidget) ---- */

QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 10px;
    top: -1px;
    background-color: {SURFACE};
}}

QTabBar::tab {{
    background-color: transparent;
    color: {TEXT_MUTED};
    padding: 8px 18px;
    margin-right: 4px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}}

QTabBar::tab:selected {{
    background-color: {SURFACE};
    color: {TEXT};
    font-weight: 600;
}}

QTabBar::tab:hover {{
    color: {TEXT};
}}

/* ---- Cards ---- */

QFrame#card {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}

QLabel#cardTitle {{
    font-size: 11pt;
    font-weight: 600;
    color: {TEXT};
    padding-bottom: 2px;
}}

/* ---- Lists ---- */

QListWidget {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
    outline: none;
}}

QListWidget::item {{
    padding: 6px 8px;
    border-radius: 6px;
}}

QListWidget::item:selected {{
    background-color: {ACCENT_SOFT};
    color: {TEXT};
}}

QListWidget::item:hover {{
    background-color: {BACKGROUND};
}}

/* ---- Checkboxes / radio buttons ---- */

QCheckBox, QRadioButton {{
    spacing: 8px;
    padding: 3px 0;
}}

QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
}}

/* ---- Date inputs ---- */

QDateEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
}}

QDateEdit:focus {{
    border: 1px solid {ACCENT};
}}

/* ---- Text areas (logs, clipping preview) ---- */

QPlainTextEdit, QTextEdit {{
    background-color: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px;
    selection-background-color: {ACCENT_SOFT};
}}

/* ---- Scrollbars (thin, unobtrusive) ---- */

QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}

QScrollBar::handle:vertical {{
    background: {BORDER_STRONG};
    border-radius: 5px;
    min-height: 24px;
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
