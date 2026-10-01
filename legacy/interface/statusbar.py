import tkinter as tk


class StatusBar(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bd=1,
            relief="sunken"
        )


        self.label = tk.Label(
            self,
            text="Ready"
        )


        self.label.pack(
            padx=10,
            pady=5,
            anchor="w"
        )


    def update(self, message):

        self.label.config(
            text=message
        )