"""Local Tkinter management of synthetic campaigns and acknowledgements.

Never launches a browser automation session or sends an external message.
"""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import storage


def run(db_path: Path) -> None:
    root = tk.Tk()
    root.title("WPS Awareness Lab | Local Operations")
    root.geometry("1010x710")
    root.minsize(790, 570)

    style = ttk.Style(root)
    if "clam" in style.theme_names():
        style.theme_use("clam")

    outer = ttk.Frame(root, padding=22)
    outer.pack(fill="both", expand=True)
    ttk.Label(outer, text="WPS / AUTHORIZED AWARENESS LAB",
              font=("Segoe UI", 17, "bold")).pack(anchor="w")
    ttk.Label(outer, text="Synthetic participants only. No personal contacts, remote sending or credential collection.").pack(
        anchor="w", pady=(5, 16))

    notebook = ttk.Notebook(outer)
    notebook.pack(fill="both", expand=True)
    tab_campaigns, tab_aliases, tab_report = (ttk.Frame(notebook, padding=16) for _ in range(3))
    notebook.add(tab_campaigns, text="Campaigns")
    notebook.add(tab_aliases, text="Demo participants")
    notebook.add(tab_report, text="Reports and privacy")

    campaign_info = ttk.Label(tab_campaigns)
    campaign_info.pack(anchor="w", pady=(0, 11))
    campaign_columns = ("id", "name", "state", "consented", "acknowledged")
    campaign_tree = ttk.Treeview(tab_campaigns, columns=campaign_columns, show="headings", height=10)
    for key, title, width in (
        ("id", "ID", 58), ("name", "Scenario", 400), ("state", "Status", 100),
        ("consented", "Consented", 105), ("acknowledged", "Acknowledged", 120)
    ):
        campaign_tree.heading(key, text=title)
        campaign_tree.column(key, width=width, stretch=(key == "name"))
    campaign_tree.pack(fill="both", expand=True)

    form = ttk.Frame(tab_campaigns)
    form.pack(fill="x", pady=(14, 6))
    ttk.Label(form, text="New fictional scenario:").pack(side="left")
    campaign_name = ttk.Entry(form, width=40)
    campaign_name.pack(side="left", padx=10, fill="x", expand=True)

    state_form = ttk.Frame(tab_campaigns)
    state_form.pack(fill="x", pady=(8, 0))
    ttk.Label(state_form, text="Selected campaign state:").pack(side="left")
    state_var = tk.StringVar(value="active")
    state_choice = ttk.Combobox(state_form, textvariable=state_var, state="readonly",
                                values=("draft", "active", "closed"), width=13)
    state_choice.pack(side="left", padx=10)

    alias_info = ttk.Label(tab_aliases, text="Select a campaign in the Campaigns tab to manage its fictional TRAIN codes.")
    alias_info.pack(anchor="w", pady=(0, 12))
    alias_tree = ttk.Treeview(tab_aliases, columns=("id", "alias", "consent"),
                              show="headings", height=12)
    for key, title, width in (("id", "ID", 70), ("alias", "Fictional alias", 200),
                              ("consent", "Demo consent", 160)):
        alias_tree.heading(key, text=title)
        alias_tree.column(key, width=width)
    alias_tree.pack(fill="both", expand=True)

    alias_form = ttk.Frame(tab_aliases)
    alias_form.pack(fill="x", pady=(14, 6))
    ttk.Label(alias_form, text="New TRAIN code:").pack(side="left")
    alias_name = ttk.Entry(alias_form, width=22)
    alias_name.pack(side="left", padx=10)
    consent_new = tk.BooleanVar(value=False)
    ttk.Checkbutton(alias_form, text="Explicit demo consent", variable=consent_new).pack(side="left", padx=10)

    alias_actions = ttk.Frame(tab_aliases)
    alias_actions.pack(fill="x", pady=(9, 0))

    def chosen_campaign_id() -> int | None:
        selected = campaign_tree.selection()
        if not selected:
            return None
        return int(campaign_tree.item(selected[0], "values")[0])

    def selected_alias() -> str | None:
        selected = alias_tree.selection()
        if not selected:
            return None
        return str(alias_tree.item(selected[0], "values")[1])

    def refresh_aliases():
        for item in alias_tree.get_children():
            alias_tree.delete(item)
        campaign_id = chosen_campaign_id()
        if campaign_id is None:
            alias_info.configure(text="Select a campaign in the Campaigns tab first.")
            return
        alias_info.configure(text=f"Fictional aliases in campaign #{campaign_id}")
        for record in storage.participants(db_path, campaign_id):
            alias_tree.insert("", "end",
                              values=(record["id"], record["alias"],
                                      "yes" if record["consent"] else "no"))

    def refresh_all():
        totals = storage.overview(db_path)
        campaign_info.configure(text=(
            f"Campaigns: {totals['campaigns']}  |  Active: {totals['active']}  |  "
            f"Consented aliases: {totals['consented_participants']}  |  "
            f"Acknowledgements: {totals['acknowledgements']}"))
        selected = chosen_campaign_id()
        for item in campaign_tree.get_children():
            campaign_tree.delete(item)
        for record in storage.campaigns(db_path):
            node = campaign_tree.insert("", "end", values=(
                record["id"], record["name"], record["state"],
                record["consented"], record["acknowledged"]))
            if record["id"] == selected:
                campaign_tree.selection_set(node)
        refresh_aliases()

    def handle_error(action):
        try:
            action()
        except (ValueError, OSError) as exc:
            messagebox.showerror("WPS local operation", str(exc), parent=root)

    def add_campaign():
        def op():
            new_id = storage.create_campaign(db_path, campaign_name.get())
            campaign_name.delete(0, "end")
            refresh_all()
            messagebox.showinfo("Draft scenario created", f"Local scenario #{new_id} created.", parent=root)
        handle_error(op)

    def change_state():
        campaign_id = chosen_campaign_id()
        if campaign_id is None:
            messagebox.showwarning("Select a campaign", "Choose a campaign row first.", parent=root)
            return
        def op():
            storage.change_campaign_state(db_path, campaign_id, state_var.get())
            refresh_all()
        handle_error(op)

    def add_alias():
        campaign_id = chosen_campaign_id()
        if campaign_id is None:
            messagebox.showwarning("Select a campaign", "Choose a campaign row first.", parent=root)
            return
        def op():
            storage.create_alias(db_path, campaign_id, alias_name.get(), consent=consent_new.get())
            alias_name.delete(0, "end")
            consent_new.set(False)
            refresh_all()
        handle_error(op)

    def change_consent(grant: bool):
        campaign_id = chosen_campaign_id()
        alias = selected_alias()
        if campaign_id is None or alias is None:
            messagebox.showwarning("Select an alias", "Choose a demo alias first.", parent=root)
            return
        if not grant and not messagebox.askyesno(
            "Revoke demo consent", "Revoke consent and delete this alias's acknowledgement history?",
            parent=root
        ):
            return
        storage.set_alias_consent(db_path, campaign_id, alias, consent=grant)
        refresh_all()

    ttk.Button(form, text="Create draft", command=add_campaign).pack(side="left")
    ttk.Button(state_form, text="Save selected state", command=change_state).pack(side="left", padx=5)
    ttk.Button(state_form, text="Refresh", command=refresh_all).pack(side="right")
    ttk.Button(alias_form, text="Add synthetic alias", command=add_alias).pack(side="left")
    ttk.Button(alias_actions, text="Grant demo consent", command=lambda: change_consent(True)).pack(side="left")
    ttk.Button(alias_actions, text="Revoke and erase events",
               command=lambda: change_consent(False)).pack(side="left", padx=9)

    ttk.Label(tab_report, text="Minimal local reporting", font=("Segoe UI", 13, "bold")).pack(anchor="w")
    ttk.Label(tab_report, text=(
        "CSV includes only scenario labels, synthetic TRAIN codes, acknowledgement type and UTC timestamp.\n"
        "No emails, phone numbers, submitted passwords, IP addresses or browsing profiles are collected."
    )).pack(anchor="w", pady=15)

    def save_report():
        target = filedialog.asksaveasfilename(
            parent=root, title="Save synthetic CSV report", defaultextension=".csv",
            filetypes=[("CSV reports", "*.csv")], initialfile="wps_demo_report.csv")
        if not target:
            return
        try:
            Path(target).write_text(storage.export_csv(db_path), encoding="utf-8-sig")
            messagebox.showinfo("Report saved", "Synthetic report saved locally.", parent=root)
        except OSError as exc:
            messagebox.showerror("Save failed", str(exc), parent=root)

    ttk.Button(tab_report, text="Export anonymized CSV", command=save_report).pack(anchor="w")
    ttk.Label(tab_report, text="Security policy: localhost only. No live message delivery or credential capture.").pack(
        anchor="w", pady=22)

    campaign_tree.bind("<<TreeviewSelect>>", lambda _event: refresh_aliases())
    refresh_all()
    root.mainloop()
