import tkinter as tk
from tkinter import ttk

from interface.menu import create_menu
from interface.statusbar import StatusBar

from interface.tabs.configuration import ConfigurationTab
from interface.tabs.results import ResultsTab
from interface.tabs.logs import LogsTab
from interface.tabs.clipping import ClippingTab
from interface.controllers.monitoring_controller import MonitoringController

class MainWindow:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Radar Gualaxo"
        )

        self.root.geometry(
            "1280x768"
        )

        self.create_layout()


    def create_layout(self):

        create_menu(
            self.root
        )

        self.notebook = ttk.Notebook(
            self.root
        )

        self.notebook.pack(
            expand=True,
            fill="both"
        )


        self.logs = LogsTab(
            self.notebook
        )


        self.configuration = ConfigurationTab(
            self.notebook
        )


        self.results = ResultsTab(
            self.notebook
        )

        self.clipping = ClippingTab(
            self.notebook
        )


        self.notebook.add(
            self.configuration,
            text="Selection"
        )

        self.notebook.add(
            self.results,
            text="Results"
        )

        self.notebook.add(
            self.logs,
            text="Logs"
        )

        self.notebook.add(
            self.clipping,
            text="Clipping"
        )

        self.statusbar = StatusBar(
            self.root
        )

        self.statusbar.pack(
            fill="x",
            side="bottom"
        )

        self.monitor = MonitoringController(
            configuration=self.configuration,
            logs=self.logs,
            notebook=self.notebook,
            results=self.results,
            clipping=self.clipping,
        )

        self.configuration.set_run_command(
            self.monitor.run_monitor
        )