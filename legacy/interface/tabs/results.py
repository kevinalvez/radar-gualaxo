import tkinter as tk
from tkinter import ttk, messagebox

from outputs.csv import CsvOutput


class ResultsTab(tk.Frame):

    def __init__(
        self,
        parent
    ):

        super().__init__(parent)

        self.results = []

        self.create_widgets()

    # ------------------------------------------------------------------

    def create_widgets(self):

        button_frame = tk.Frame(self)
        button_frame.pack(
            fill="x",
            padx=10,
            pady=5,
        )

        self.export_button = tk.Button(
            button_frame,
            text="Exportar CSV",
            state="disabled",
            command=self.export_csv,
        )

        self.export_button.pack(side="right")

        columns = (
            "source",
            "title",
            "keyword",
            "excerpt",
        )

        self.table = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
        )

        self.table.heading("source", text="Source")
        self.table.heading("title", text="Title")
        self.table.heading("keyword", text="Keyword")
        self.table.heading("excerpt", text="Excerpt")

        self.table.column("source", width=150)
        self.table.column("title", width=350)
        self.table.column("keyword", width=180)
        self.table.column("excerpt", width=500)

        self.table.pack(
            expand=True,
            fill="both",
            padx=10,
            pady=(0, 10),
        )

    # ------------------------------------------------------------------

    def show_results(
        self,
        processed_publications,
    ):

        self.clear()

        self.results = processed_publications

        for processed in processed_publications:

            publication = processed.publication

            for result in processed.keyword_results():

                self.table.insert(
                    "",
                    "end",
                    values=(
                        publication.source_name,
                        publication.title,
                        result.value,
                        result.metadata.get(
                            "excerpt",
                            "",
                        ),
                    ),
                )

        if self.results:
            self.export_button.config(state="normal")

    # ------------------------------------------------------------------

    def clear(self):

        self.results = []

        for item in self.table.get_children():

            self.table.delete(item)

        self.export_button.config(state="disabled")

    # ------------------------------------------------------------------

    def export_csv(self):

        if not self.results:

            messagebox.showwarning(
                "Radar Gualaxo",
                "Não há resultados para exportar.",
            )

            return

        output = CsvOutput("output/results.csv")

        output.export(self.results)

        messagebox.showinfo(
            "Radar Gualaxo",
            "CSV exportado para output/results.csv",
        )