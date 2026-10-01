"""
interface/tabs/clipping.py

Clipping interface tab.

Responsible for displaying processed monitoring results
in a format ready for WhatsApp sharing.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from datetime import datetime


class ClippingTab(ttk.Frame):
    """
    Tab responsible for clipping generation and preview.
    """


    def __init__(
        self,
        parent,
    ):

        super().__init__(
            parent
        )


        self.results = []


        self.create_layout()


    # -------------------------------------------------------------

    def create_layout(self):


        # -----------------------------
        # Header
        # -----------------------------

        header = ttk.LabelFrame(
            self,
            text="Clipping"
        )

        header.pack(
            fill="x",
            padx=10,
            pady=10
        )


        ttk.Label(
            header,
            text="Período:"
        ).pack(
            side="left",
            padx=5
        )


        self.period = ttk.Entry(
            header,
            width=20
        )

        self.period.pack(
            side="left"
        )


        self.period.insert(
            0,
            datetime.now().strftime(
                "%d/%m/%Y"
            )
        )


        # -----------------------------
        # Buttons
        # -----------------------------


        ttk.Button(
            header,
            text="Gerar Clipping",
            command=self.generate
        ).pack(
            side="left",
            padx=10
        )


        ttk.Button(
            header,
            text="Copiar WhatsApp",
            command=self.copy_clipboard
        ).pack(
            side="left",
            padx=5
        )


        ttk.Button(
            header,
            text="Exportar TXT",
            command=self.export_txt
        ).pack(
            side="left",
            padx=5
        )


        # -----------------------------
        # Preview
        # -----------------------------


        preview_frame = ttk.LabelFrame(
            self,
            text="Prévia"
        )

        preview_frame.pack(
            expand=True,
            fill="both",
            padx=10,
            pady=10
        )


        self.preview = tk.Text(
            preview_frame,
            wrap="word"
        )

        self.preview.pack(
            expand=True,
            fill="both",
            padx=5,
            pady=5
        )


    # -------------------------------------------------------------

    def set_results(
        self,
        results,
    ):
        """
        Receives processed publications
        from pipeline.
        """

        self.results = results


    # -------------------------------------------------------------

    def generate(self):

        if not self.results:

            messagebox.showwarning(
                "Clipping",
                "Nenhum resultado disponível."
            )

            return


        text = self.build_clipping()


        self.preview.delete(
            "1.0",
            tk.END
        )


        self.preview.insert(
            tk.END,
            text
        )


    # -------------------------------------------------------------

    def build_clipping(self):

        lines = []


        lines.append(
            "📌 *Clipping – Radar Gualaxo*"
        )


        lines.append(
            f"📅 *{self.period.get()}*"
        )


        lines.append("")


        categories = {}


        for processed in self.results:


            publication = processed.publication


            for result in processed.keyword_results():

                category = (
                    result.metadata.get("category")
                    or publication.category
                    or "Outros Temas"
                )


                emoji = result.metadata.get(
                    "emoji",
                    "📌"
                )


                if category not in categories:

                    categories[category] = {
                        "emoji": emoji,
                        "items": []
                    }


                summary = ""

                for publication_result in processed.results:

                    if publication_result.type == "summary":

                        summary = publication_result.value


                categories[category]["items"].append(
                    {
                        "title": publication.title,
                        "source": publication.source_name,
                        "url": publication.url,
                        "summary": summary,
                    }
                )



        for category, data in categories.items():


            lines.append(
                f"{data['emoji']} *{category}*"
            )


            lines.append("")


            for item in data["items"]:


                lines.append(
                    f"• {item['title']}"
                )


                lines.append(
                    f"   o Veículo: {item['source']}"
                )


                lines.append(
                    f"   o Link: {item['url']}"
                )

                if item.get("summary"):

                    lines.append(
                        f"   o Resumo: {item['summary']}"
                    )


                lines.append("")



        return "\n".join(
            lines
        )


    # -------------------------------------------------------------

    def copy_clipboard(self):

        text = self.preview.get(
            "1.0",
            tk.END
        )


        self.clipboard_clear()

        self.clipboard_append(
            text
        )


        messagebox.showinfo(
            "WhatsApp",
            "Clipping copiado."
        )


    # -------------------------------------------------------------

    def export_txt(self):


        text = self.preview.get(
            "1.0",
            tk.END
        )


        if not text.strip():

            messagebox.showwarning(
                "Exportar",
                "Gere o clipping primeiro."
            )

            return



        file = filedialog.asksaveasfilename(
            title="Salvar clipping",
            defaultextension=".txt",
            filetypes=[
                (
                    "Arquivo texto",
                    "*.txt"
                )
            ]
        )


        if not file:

            return



        with open(
            file,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                text
            )


        messagebox.showinfo(
            "Exportar",
            "Arquivo salvo."
        )