import tkinter as tk
from tkinter import simpledialog, messagebox
from interface.source_dialog import SourceDialog

from config.sources import (
    load_sources,
    add_source,
    remove_source,
    update_source,
)

from config.keywords import (
    load_keywords,
    add_keyword,
    remove_keyword,
    update_keyword,
)


class ConfigurationTab(tk.Frame):

    def __init__(
        self,
        parent
    ):

        super().__init__(
            parent
        )

        self.keyword_vars = {}

        self.period_var = tk.StringVar(
            value="7_days"
        )

        self.interval_frame = None

        self.create_widgets()

        self.refresh_sources()

        self.refresh_keywords()



    # =====================================================
    # UI
    # =====================================================

    def create_widgets(self):

        container = tk.Frame(
            self
        )

        container.pack(
            expand=True,
            fill="both",
            padx=20,
            pady=20
        )


        # -------------------------
        # SOURCES
        # -------------------------

        sources_frame = tk.LabelFrame(
            container,
            text="Sources"
        )

        sources_frame.pack(
            side="left",
            expand=True,
            fill="both",
            padx=10
        )


        self.sources_list = tk.Listbox(
            sources_frame,
            height=15
        )

        self.sources_list.pack(
            expand=True,
            fill="both",
            padx=10,
            pady=10
        )


        source_buttons = tk.Frame(
            sources_frame
        )

        source_buttons.pack(
            pady=5
        )


        tk.Button(
            source_buttons,
            text="Add",
            width=10,
            command=self.add_source_ui
        ).pack(
            side="left",
            padx=3
        )


        tk.Button(
            source_buttons,
            text="Edit",
            width=10,
            command=self.edit_source_ui
        ).pack(
            side="left",
            padx=3
        )


        tk.Button(
            source_buttons,
            text="Remove",
            width=10,
            command=self.remove_source_ui
        ).pack(
            side="left",
            padx=3
        )



        # -------------------------
        # KEYWORDS
        # -------------------------

        keywords_frame = tk.LabelFrame(
            container,
            text="Keywords"
        )

        keywords_frame.pack(
            side="right",
            expand=True,
            fill="both",
            padx=10
        )


        self.keywords_container = tk.Frame(
            keywords_frame
        )

        self.keywords_container.pack(
            expand=True,
            fill="both",
            padx=10,
            pady=10
        )


        keyword_buttons = tk.Frame(
            keywords_frame
        )

        keyword_buttons.pack(
            pady=5
        )


        tk.Button(
            keyword_buttons,
            text="Add",
            width=10,
            command=self.add_keyword_ui
        ).pack(
            side="left",
            padx=3
        )


        tk.Button(
            keyword_buttons,
            text="Edit",
            width=10,
            command=self.edit_keyword_ui
        ).pack(
            side="left",
            padx=3
        )


        tk.Button(
            keyword_buttons,
            text="Remove",
            width=10,
            command=self.remove_keyword_ui
        ).pack(
            side="left",
            padx=3
        )
        # -------------------------
        # SEARCH PERIOD
        # -------------------------

        period_frame = tk.LabelFrame(
            container,
            text="Search Period"
        )

        period_frame.pack(
            side="bottom",
            fill="x",
            padx=10,
            pady=10
        )


        tk.Radiobutton(
            period_frame,
            text="Últimas 24 horas",
            variable=self.period_var,
            value="24h",
            command=self.toggle_interval
        ).pack(
            anchor="w"
        )


        tk.Radiobutton(
            period_frame,
            text="Últimos 7 dias",
            variable=self.period_var,
            value="7_days",
            command=self.toggle_interval
        ).pack(
            anchor="w"
        )


        tk.Radiobutton(
            period_frame,
            text="Últimos 30 dias",
            variable=self.period_var,
            value="30_days",
            command=self.toggle_interval
        ).pack(
            anchor="w"
        )


        tk.Radiobutton(
            period_frame,
            text="Intervalo",
            variable=self.period_var,
            value="custom",
            command=self.toggle_interval
        ).pack(
            anchor="w"
        )


        self.interval_frame = tk.Frame(
            period_frame
        )

        self.create_date_fields()
        
        bottom = tk.Frame(self)

        bottom.pack(
            side="bottom",
            fill="x",
            padx=10,
            pady=10,
        )

        self.run_button = tk.Button(
            bottom,
            text="▶ RUN MONITOR",
            width=22,
            height=2
        )

        self.run_button.pack(
            anchor="e"
        )



    # =====================================================
    # SOURCES
    # =====================================================

    def refresh_sources(self):

        self.sources_list.delete(
            0,
            "end"
        )


        for source in load_sources():

            self.sources_list.insert(
                "end",
                source.get(
                    "name",
                    ""
                )
            )



    def add_source_ui(self):

        dialog = SourceDialog(
            self
        )

        self.wait_window(
            dialog
        )


        if dialog.result:

            add_source(
                dialog.result
            )

            self.refresh_sources()



    def edit_source_ui(self):

        selected = self.sources_list.curselection()


        if not selected:

            return


        name = self.sources_list.get(
            selected[0]
        )


        source = next(

            item

            for item in load_sources()

            if item.get("name") == name

        )


        dialog = SourceDialog(
            self,
            source
        )


        self.wait_window(
            dialog
        )


        if dialog.result:

            update_source(
                name,
                dialog.result
            )

            self.refresh_sources()



    def remove_source_ui(self):

        selected = (
            self.sources_list.curselection()
        )


        if not selected:

            return


        name = self.sources_list.get(
            selected[0]
        )

        remove_source(
            name
        )


        self.refresh_sources()



    # =====================================================
    # KEYWORDS
    # =====================================================

    def refresh_keywords(self):

        for widget in (
            self.keywords_container
            .winfo_children()
        ):

            widget.destroy()


        self.keyword_vars.clear()


        for keyword in load_keywords():

            var = tk.BooleanVar(
                value=False
            )


            checkbox = tk.Checkbutton(
                self.keywords_container,
                text=keyword,
                variable=var
            )


            checkbox.pack(
                anchor="w"
            )


            self.keyword_vars[keyword] = var



    def add_keyword_ui(self):

        value = simpledialog.askstring(
            "Add Keyword",
            "Keyword:"
        )


        if value:

            add_keyword(
                value
            )

            self.refresh_keywords()



    def edit_keyword_ui(self):

        selected = self.get_selected_keyword_name()


        if not selected:

            messagebox.showwarning(
                "Keyword",
                "Selecione uma keyword."
            )

            return


        new = simpledialog.askstring(
            "Edit Keyword",
            "Novo valor:",
            initialvalue=selected
        )


        if new:

            update_keyword(
                selected,
                new
            )

            self.refresh_keywords()



    def remove_keyword_ui(self):

        selected = self.get_selected_keyword_name()


        if selected:

            remove_keyword(
                selected
            )

            self.refresh_keywords()



    def get_selected_keyword_name(self):

        for keyword, var in self.keyword_vars.items():

            if var.get():

                return keyword


        return None



    # =====================================================
    # PIPELINE INTERFACE
    # =====================================================

    def get_selected_keywords(self):

        return [

            keyword

            for keyword, var

            in self.keyword_vars.items()

            if var.get()

        ]

    def set_run_command(
        self,
        command,
    ):
        self.run_button.configure(
            command=command
        )
    
    def create_date_fields(self):

        self.start_date_label = tk.Label(
            self.interval_frame,
            text="Data inicial:"
        )

        self.start_date_entry = tk.Entry(
            self.interval_frame,
            width=12,
            validate="key",
            validatecommand=(
                self.register(self.date_mask),
                "%P"
            )
        )


        self.end_date_label = tk.Label(
            self.interval_frame,
            text="Data final:"
        )

        self.end_date_entry = tk.Entry(
            self.interval_frame,
            width=12,
            validate="key",
            validatecommand=(
                self.register(self.date_mask),
                "%P"
            )
        )


    def toggle_interval(self):

        if self.period_var.get() == "custom":

            self.interval_frame.pack(
                padx=20,
                pady=5
            )

            self.start_date_label.grid(
                row=0,
                column=0,
                padx=5
            )

            self.start_date_entry.grid(
                row=0,
                column=1,
                padx=5
            )

            self.end_date_label.grid(
                row=1,
                column=0,
                padx=5
            )

            self.end_date_entry.grid(
                row=1,
                column=1,
                padx=5
            )

        else:

            self.interval_frame.pack_forget()



    def date_mask(self, value):

        if len(value) > 10:
            return False


        allowed = (
            value
            .replace("/", "")
        )


        if not allowed.isdigit():
            return False


        if len(value) in (2, 5):

            self.after(
                1,
                lambda: None
            )


        return True

    def get_selected_period(self):

        return {
            "period": self.period_var.get(),
            "start_date": self.start_date_entry.get(),
            "end_date": self.end_date_entry.get(),
        }