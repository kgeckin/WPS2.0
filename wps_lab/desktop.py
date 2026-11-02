"""A lightweight read-only Tkinter companion to the web console."""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk

from . import storage


def run(db_path: Path) -> None:
    root = tk.Tk()
    root.title("WPS Awareness Lab | Local Operations")
    root.geometry("870x540")
    root.configure(bg="#111D29")
    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")
    main = ttk.Frame(root, padding=24)
    main.pack(fill="both", expand=True)
    ttk.Label(main, text="WPS / AUTHORIZED AWARENESS LAB",
              font=("Segoe UI", 15, "bold")).pack(anchor="w")
    ttk.Label(main, text="Local synthetic campaign overview. No external messaging or credential collection.").pack(anchor="w", pady=(8, 20))
    labels = ttk.Label(main, text="")
    labels.pack(anchor="w", pady=8)
    tree = ttk.Treeview(main, columns=("campaign", "state", "consented", "acknowledged"), show="headings")
    for key, title, width in (("campaign", "Campaign", 360), ("state", "State", 110),
                              ("consented", "Consented aliases", 160),
                              ("acknowledged", "Acknowledged", 160)):
        tree.heading(key, text=title)
        tree.column(key, width=width, stretch=True)
    tree.pack(fill="both", expand=True)

    def refresh():
        summary = storage.overview(db_path)
        labels.configure(text=(f"Campaigns: {summary['campaigns']}  |  Active: {summary['active']}  |  "
                               f"Consented demo aliases: {summary['consented_participants']}  |  "
                               f"Acknowledgements: {summary['acknowledgements']}"))
        for item in tree.get_children():
            tree.delete(item)
        for campaign in storage.campaigns(db_path):
            tree.insert("", "end", values=(campaign["name"], campaign["state"],
                                           campaign["consented"], campaign["acknowledged"]))

    ttk.Button(main, text="Refresh local data", command=refresh).pack(anchor="e", pady=(12, 0))
    refresh()
    root.mainloop()
