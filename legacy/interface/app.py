import tkinter as tk

from interface.main_window import MainWindow


def start():
    root = tk.Tk()

    app = MainWindow(root)

    root.mainloop()

    return app