import tkinter as tk


class LogsTab(tk.Frame):

    def __init__(
        self,
        parent
    ):

        super().__init__(
            parent
        )

        self.text = tk.Text(
            self
        )

        self.text.pack(
            expand=True,
            fill="both",
            padx=10,
            pady=10
        )


    def write(
        self,
        message
    ):

        self.text.insert(
            "end",
            message
        )

        self.text.see(
            "end"
        )