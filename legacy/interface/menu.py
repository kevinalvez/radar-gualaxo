import tkinter as tk


def create_menu(root):

    menu_bar = tk.Menu(root)


    file_menu = tk.Menu(
        menu_bar,
        tearoff=0
    )

    file_menu.add_command(
        label="Exit",
        command=root.destroy
    )


    menu_bar.add_cascade(
        label="File",
        menu=file_menu
    )


    help_menu = tk.Menu(
        menu_bar,
        tearoff=0
    )

    help_menu.add_command(
        label="About",
        command=lambda:
            print("Radar Gualaxo")
    )


    menu_bar.add_cascade(
        label="Help",
        menu=help_menu
    )


    root.config(
        menu=menu_bar
    )