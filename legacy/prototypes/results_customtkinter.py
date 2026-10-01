"""
prototypes/results_customtkinter.py

Prototype: Results tab rebuilt with CustomTkinter.

CustomTkinter has no built-in table/grid widget, so the "table" here
is built manually with a scrollable frame of label rows. This is the
honest trade-off of this option: modern-looking buttons/inputs, but
tables still need to be hand-rolled (or you fall back to a plain
ttk.Treeview, which looks visually inconsistent with the rest).

Run: python prototypes/results_customtkinter.py
"""

import customtkinter as ctk

from sample_data import ROWS

customtkinter_appearance = ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

COLUMNS = ("Fonte", "Título", "Keyword", "Excerto")
COLUMN_WEIGHTS = (1, 3, 1, 4)


class ResultsPrototype(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Radar Gualaxo — Protótipo Resultados (CustomTkinter)")
        self.geometry("1100x600")

        self.all_rows = ROWS
        self.row_widgets = []

        self._build_toolbar()
        self._build_table()
        self._render_rows(self.all_rows)

    # ------------------------------------------------------------

    def _build_toolbar(self):
        toolbar = ctk.CTkFrame(self)
        toolbar.pack(fill="x", padx=12, pady=(12, 6))

        ctk.CTkLabel(toolbar, text="Buscar:").pack(side="left", padx=(4, 8))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._apply_filter())

        search_entry = ctk.CTkEntry(
            toolbar, textvariable=self.search_var,
            placeholder_text="filtrar por título, fonte ou keyword...",
            width=400,
        )
        search_entry.pack(side="left", padx=4)

        ctk.CTkButton(
            toolbar, text="Exportar CSV", command=lambda: None,
        ).pack(side="right", padx=4)

    # ------------------------------------------------------------

    def _build_table(self):
        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=12)

        for text, weight in zip(COLUMNS, COLUMN_WEIGHTS):
            header.grid_columnconfigure(COLUMNS.index(text), weight=weight)
            ctk.CTkLabel(
                header, text=text, font=ctk.CTkFont(weight="bold"),
            ).grid(row=0, column=COLUMNS.index(text), sticky="w", padx=8, pady=4)

        self.table_frame = ctk.CTkScrollableFrame(self)
        self.table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        for i, weight in enumerate(COLUMN_WEIGHTS):
            self.table_frame.grid_columnconfigure(i, weight=weight)

    # ------------------------------------------------------------

    def _render_rows(self, rows):
        for widget in self.row_widgets:
            widget.destroy()
        self.row_widgets = []

        for row_index, (source, title, keyword, excerpt) in enumerate(rows):
            values = (source, title, keyword, excerpt)
            for col_index, value in enumerate(values):
                label = ctk.CTkLabel(
                    self.table_frame,
                    text=value,
                    anchor="w",
                    justify="left",
                    wraplength=260 if col_index in (1, 3) else 140,
                )
                label.grid(
                    row=row_index, column=col_index,
                    sticky="w", padx=8, pady=6,
                )
                self.row_widgets.append(label)

    # ------------------------------------------------------------

    def _apply_filter(self):
        term = self.search_var.get().lower().strip()

        if not term:
            self._render_rows(self.all_rows)
            return

        filtered = [
            row for row in self.all_rows
            if any(term in str(value).lower() for value in row)
        ]
        self._render_rows(filtered)


if __name__ == "__main__":
    app = ResultsPrototype()
    app.mainloop()
