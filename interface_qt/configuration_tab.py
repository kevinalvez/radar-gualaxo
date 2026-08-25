"""
interface_qt/configuration_tab.py

Configuration/Selection tab, rebuilt in PySide6.

Same public API the MonitoringController relies on (see
interface/controllers/monitoring_controller.py): get_selected_keywords(),
get_selected_period(), set_run_command(callback).

Usability changes versus the Tkinter version:
- Keywords are a checkable, scrollable QListWidget instead of a plain
  stack of checkboxes with no scroll (which would overflow off-screen
  once the keyword list grows).
- The custom date range uses QDateEdit (calendar popup) instead of
  free-text fields with a hand-rolled digit mask.
- Sources are checkable too (get_selected_sources()), letting a run
  narrow down which enabled sources to include - the Tkinter version
  never had this, it always ran every enabled source in sources.json.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QRadioButton, QButtonGroup, QDateEdit, QLabel,
    QInputDialog, QMessageBox, QStackedWidget,
)

from config.sources import load_sources, add_source, remove_source, update_source
from config.keywords import load_keywords, add_keyword, remove_keyword, update_keyword

from interface_qt.widgets import Card
from interface_qt.source_dialog import SourceDialog

PERIOD_OPTIONS = [
    ("24h", "Últimas 24 horas"),
    ("7_days", "Últimos 7 dias"),
    ("30_days", "Últimos 30 dias"),
    ("custom", "Intervalo personalizado"),
]


class ConfigurationTab(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._run_command = None

        self._build_ui()
        self.refresh_sources()
        self.refresh_keywords()

    # ------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        columns = QHBoxLayout()
        columns.setSpacing(12)
        columns.addWidget(self._build_sources_card(), stretch=1)
        columns.addWidget(self._build_keywords_card(), stretch=1)
        layout.addLayout(columns, stretch=1)

        layout.addWidget(self._build_period_card())
        layout.addLayout(self._build_run_row())

    # ------------------------------------------------------------
    # SOURCES
    # ------------------------------------------------------------

    def _build_sources_card(self):
        card = Card("Fontes")

        self.sources_list = QListWidget()
        card.body.addWidget(self.sources_list, stretch=1)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Adicionar")
        add_btn.clicked.connect(self._add_source)
        edit_btn = QPushButton("Editar")
        edit_btn.clicked.connect(self._edit_source)
        remove_btn = QPushButton("Remover")
        remove_btn.clicked.connect(self._remove_source)

        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(remove_btn)
        card.body.addLayout(buttons)

        return card

    def refresh_sources(self):
        previously_checked = self._checked_source_names_before_refresh()

        self.sources_list.clear()

        for source in load_sources():
            name = source.get("name", "")
            enabled = source.get("enabled", True)

            label = name if enabled else f"{name}  (desativada)"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, name)

            if enabled:
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                checked = (
                    name in previously_checked
                    if previously_checked is not None
                    else True
                )
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
            else:
                item.setForeground(Qt.gray)

            self.sources_list.addItem(item)

    def _checked_source_names_before_refresh(self):
        """
        Returns the set of currently-checked source names, or None
        before the list has ever been populated, so refresh_sources()
        knows to default everything to checked instead of "restoring"
        an empty selection.
        """

        if self.sources_list.count() == 0:
            return None

        return {
            self.sources_list.item(i).data(Qt.UserRole)
            for i in range(self.sources_list.count())
            if self.sources_list.item(i).checkState() == Qt.Checked
        }

    def _add_source(self):
        dialog = SourceDialog(self)

        if dialog.exec() == SourceDialog.Accepted and dialog.result:
            add_source(dialog.result)
            self.refresh_sources()

    def _selected_source_name(self):
        item = self.sources_list.currentItem()
        if item is None:
            return None
        return item.data(Qt.UserRole)

    def _edit_source(self):
        name = self._selected_source_name()
        if not name:
            return

        source = next(
            (item for item in load_sources() if item.get("name") == name),
            None,
        )
        if source is None:
            return

        dialog = SourceDialog(self, source)

        if dialog.exec() == SourceDialog.Accepted and dialog.result:
            update_source(name, dialog.result)
            self.refresh_sources()

    def _remove_source(self):
        name = self._selected_source_name()
        if not name:
            return

        remove_source(name)
        self.refresh_sources()

    # ------------------------------------------------------------
    # KEYWORDS
    # ------------------------------------------------------------

    def _build_keywords_card(self):
        card = Card("Keywords")

        self.keywords_list = QListWidget()
        card.body.addWidget(self.keywords_list, stretch=1)

        buttons = QHBoxLayout()
        add_btn = QPushButton("Adicionar")
        add_btn.clicked.connect(self._add_keyword)
        edit_btn = QPushButton("Editar")
        edit_btn.clicked.connect(self._edit_keyword)
        remove_btn = QPushButton("Remover")
        remove_btn.clicked.connect(self._remove_keyword)

        buttons.addWidget(add_btn)
        buttons.addWidget(edit_btn)
        buttons.addWidget(remove_btn)
        card.body.addLayout(buttons)

        return card

    def refresh_keywords(self):
        self.keywords_list.clear()

        for keyword in load_keywords():
            item = QListWidgetItem(keyword)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.keywords_list.addItem(item)

    def _add_keyword(self):
        value, ok = QInputDialog.getText(self, "Adicionar keyword", "Keyword:")

        if ok and value.strip():
            add_keyword(value.strip())
            self.refresh_keywords()

    def _selected_keyword_item(self):
        return self.keywords_list.currentItem()

    def _edit_keyword(self):
        item = self._selected_keyword_item()
        if item is None:
            QMessageBox.warning(self, "Keyword", "Selecione uma keyword.")
            return

        current = item.text()
        value, ok = QInputDialog.getText(
            self, "Editar keyword", "Novo valor:", text=current
        )

        if ok and value.strip():
            update_keyword(current, value.strip())
            self.refresh_keywords()

    def _remove_keyword(self):
        item = self._selected_keyword_item()
        if item is None:
            QMessageBox.warning(self, "Keyword", "Selecione uma keyword.")
            return

        remove_keyword(item.text())
        self.refresh_keywords()

    # ------------------------------------------------------------
    # SEARCH PERIOD
    # ------------------------------------------------------------

    def _build_period_card(self):
        card = Card("Período de busca")

        self.period_group = QButtonGroup(self)
        self._period_buttons = {}

        for value, label in PERIOD_OPTIONS:
            radio = QRadioButton(label)
            self.period_group.addButton(radio)
            self._period_buttons[radio] = value
            card.body.addWidget(radio)

        # Built before any radio fires toggled (see below) - the
        # handler references this stack, so it must exist first or
        # the very first setChecked() call below fails to build it.
        self.custom_range_stack = QStackedWidget()
        empty_page = QWidget()
        range_page = self._build_date_range_row()
        self.custom_range_stack.addWidget(empty_page)
        self.custom_range_stack.addWidget(range_page)
        card.body.addWidget(self.custom_range_stack)

        for radio in self._period_buttons:
            radio.toggled.connect(self._on_period_changed)

        # default: "Últimos 7 dias"
        for radio, value in self._period_buttons.items():
            if value == "7_days":
                radio.setChecked(True)

        return card

    def _build_date_range_row(self):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 0)

        layout.addWidget(QLabel("De:"))
        self.start_date = QDateEdit(calendarPopup=True)
        self.start_date.setDisplayFormat("dd/MM/yyyy")
        self.start_date.setDate(QDate.currentDate().addDays(-7))
        layout.addWidget(self.start_date)

        layout.addWidget(QLabel("Até:"))
        self.end_date = QDateEdit(calendarPopup=True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date.setDate(QDate.currentDate())
        layout.addWidget(self.end_date)

        layout.addStretch()

        return row

    def _on_period_changed(self):
        if self._selected_period_value() == "custom":
            self.custom_range_stack.setCurrentIndex(1)
        else:
            self.custom_range_stack.setCurrentIndex(0)

    def _selected_period_value(self):
        checked = self.period_group.checkedButton()
        return self._period_buttons.get(checked, "7_days")

    # ------------------------------------------------------------
    # RUN
    # ------------------------------------------------------------

    def _build_run_row(self):
        row = QHBoxLayout()
        row.addStretch()

        self.run_button = QPushButton("▶  Executar Monitoramento")
        self.run_button.setObjectName("primaryButton")
        self.run_button.setMinimumHeight(38)
        self.run_button.clicked.connect(self._on_run_clicked)
        row.addWidget(self.run_button)

        return row

    def _on_run_clicked(self):
        if self._run_command:
            self._run_command()

    # ------------------------------------------------------------
    # Public API (mirrors interface/tabs/configuration.py)
    # ------------------------------------------------------------

    def get_selected_keywords(self):
        selected = []
        for i in range(self.keywords_list.count()):
            item = self.keywords_list.item(i)
            if item.checkState() == Qt.Checked:
                selected.append(item.text())
        return selected

    def get_selected_sources(self):
        selected = []
        for i in range(self.sources_list.count()):
            item = self.sources_list.item(i)
            if item.flags() & Qt.ItemIsUserCheckable and item.checkState() == Qt.Checked:
                selected.append(item.data(Qt.UserRole))
        return selected

    def get_selected_period(self):
        period = self._selected_period_value()
        return {
            "period": period,
            "start_date": self.start_date.date().toString("dd/MM/yyyy"),
            "end_date": self.end_date.date().toString("dd/MM/yyyy"),
        }

    def set_run_command(self, command):
        self._run_command = command

    def set_running(self, running: bool) -> None:
        """
        Reflects whether a monitoring run is currently in progress on
        a background thread - disables the run button (so a second
        run can't be started concurrently) and updates its label.
        """

        self.run_button.setEnabled(not running)
        self.run_button.setText(
            "Executando..." if running else "▶  Executar Monitoramento"
        )
