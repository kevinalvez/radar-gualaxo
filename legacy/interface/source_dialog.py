import tkinter as tk
from tkinter import ttk


class SourceDialog(tk.Toplevel):

    def __init__(
        self,
        parent,
        source=None
    ):

        super().__init__(
            parent
        )

        self.title(
            "Source"
        )

        self.geometry(
            "400x350"
        )

        self.result = None

        self.source = source

        self.create_widgets()


        if source:
            self.load_source()



    def create_widgets(self):

        container = tk.Frame(
            self
        )

        container.pack(
            padx=20,
            pady=20,
            fill="both"
        )


        # nome

        tk.Label(
            container,
            text="Nome:"
        ).pack(
            anchor="w"
        )


        self.name_entry = tk.Entry(
            container
        )

        self.name_entry.pack(
            fill="x"
        )


        # provider

        tk.Label(
            container,
            text="Provider:"
        ).pack(
            anchor="w",
            pady=(10,0)
        )


        self.provider_combo = ttk.Combobox(
            container,
            values=[
                "rss",
                "html",
                "sitemap",
                "api",
                "search",
                "pdf"
            ],
            state="readonly"
        )

        self.provider_combo.pack(
            fill="x"
        )

        self.provider_combo.set(
            "rss"
        )


        # url

        tk.Label(
            container,
            text="URL:"
        ).pack(
            anchor="w",
            pady=(10,0)
        )


        self.url_entry = tk.Entry(
            container
        )

        self.url_entry.pack(
            fill="x"
        )


        # categoria

        tk.Label(
            container,
            text="Categoria:"
        ).pack(
            anchor="w",
            pady=(10,0)
        )


        self.category_entry = tk.Entry(
            container
        )

        self.category_entry.pack(
            fill="x"
        )


        # descrição

        tk.Label(
            container,
            text="Descrição:"
        ).pack(
            anchor="w",
            pady=(10,0)
        )


        self.description_entry = tk.Entry(
            container
        )

        self.description_entry.pack(
            fill="x"
        )


        tk.Button(
            container,
            text="Salvar",
            command=self.save
        ).pack(
            pady=20
        )



    def load_source(self):

        self.name_entry.insert(
            0,
            self.source.get("name","")
        )

        self.provider_combo.set(
            self.source.get(
                "provider",
                "rss"
            )
        )

        self.url_entry.insert(
            0,
            self.source.get("url","")
        )

        self.category_entry.insert(
            0,
            self.source.get(
                "category",
                ""
            )
        )

        self.description_entry.insert(
            0,
            self.source.get(
                "description",
                ""
            )
        )



    def save(self):

        self.result = {

            "name":
                self.name_entry.get(),

            "provider":
                self.provider_combo.get(),

            "url":
                self.url_entry.get(),

            "enabled":
                True,

            "category":
                self.category_entry.get(),

            "description":
                self.description_entry.get()

        }


        self.destroy()