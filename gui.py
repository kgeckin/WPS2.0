""" WPS – WhatsApp Phishing Awareness Simulator (GUI)

Users tab upgrades in this version:
- Excel-style filter popover on column headers (left-click OR right-click header)
- Values in the popover reflect rows visible under other active filters (Excel behavior)
- Checkbox column with header master checkbox (select/unselect all visible)
- Row actions: Edit | Delete (left half = Edit, right half = Delete), double-click = Edit
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import os
import threading
import logging
from logging.handlers import RotatingFileHandler
import pandas as pd
from db_utils import log_error 

from db_utils import (
    fetch_all_users,
    fetch_all_campaigns,
    add_user,
    add_campaign,
    update_user,
    delete_user,
    delete_campaign,
    fetch_campaign_status,
    fetch_error_logs,
    log_error
)
from sender import run_whatsapp_campaign


class WPSGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WPS – WhatsApp Phishing Awareness Simulator")
        self.geometry("1220x800")
        self.configure(bg="#f4f4f4")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.users_frame = ttk.Frame(self.notebook)
        self.campaigns_frame = ttk.Frame(self.notebook)
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.run_output_frame = ttk.Frame(self.notebook)

        self.notebook.add(self.users_frame, text="Users")
        self.notebook.add(self.campaigns_frame, text="Campaigns")
        self.notebook.add(self.dashboard_frame, text="Dashboard")
        self.notebook.add(self.run_output_frame, text="Run Output")

        # Users tab state
        self.users_data = []
        self.user_checked = set()
        # {column_name: set(allowed_values) or None}
        self._filter_state = {}
        self._header_check_all = False

        self._init_checkbox_images()
        self._init_users_tab()
        self._init_campaigns_tab()
        self._init_dashboard_tab()
        self._init_run_output_tab()

        # Admin tab toggle
        self.admin_tab_added = False
        self.admin_tab_index = None
        ttk.Button(self, text="Admin Tools", command=self.unlock_admin_tab).pack(
            side="bottom", anchor="e", padx=12, pady=8
        )

        self._setup_logging()

    # ---------- Logging ----------
    def _setup_logging(self):
        logger = logging.getLogger("WPS")
        logger.setLevel(logging.INFO)
        logs_dir = os.path.join(os.path.dirname(__file__), "logs")
        os.makedirs(logs_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(logs_dir, "wps_run.log"),
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )

        class TkTextHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget

            def emit(self, record):
                msg = self.format(record)
                try:
                    self.text_widget.after(
                        0,
                        lambda: (
                            self.text_widget.insert(tk.END, msg + "\n"),
                            self.text_widget.see(tk.END),
                        ),
                    )
                except Exception:
                    pass

        tk_handler = TkTextHandler(self.run_output_text)
        tk_handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )

        class DBLogHandler(logging.Handler):
            """Persist ERROR+ log records to MySQL error_logs."""
            def emit(self, record):
                try:
                    if record.levelno >= logging.ERROR:
                        msg = self.format(record)
                        stack = getattr(record, "exc_text", "") or ""
                        log_error(msg, stack, component="GUI/Run")
                except Exception:
                    pass

        db_handler = DBLogHandler()
        db_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

        types = {type(h) for h in logger.handlers}
        if RotatingFileHandler not in types:
            logger.addHandler(file_handler)
        if TkTextHandler not in types:
            logger.addHandler(tk_handler)
        if DBLogHandler not in types:        
            logger.addHandler(db_handler)

    # ---------- Users ----------
    def _init_checkbox_images(self):
        # 16x16 base64 PNGs for unchecked/checked boxes
        unchecked_b64 = (
            "R0lGODlhDAAMAIABAAAAAP///yH5BAEKAAEALAAAAAAMAAwAAAIajI+py+0Po5y02ouz3rz7D4bi"
            "SJbmqpnrqrbuC8fyrAADs="
        )
        checked_b64 = (
            "R0lGODlhDAAMAIABAAAAAP///yH5BAEKAAEALAAAAAAMAAwAAAIdjI+py+0Po5y02ouz3rz7D4bi"
            "SJbmqpnrqrbuC8fzbAAAOw=="
        )
        self.img_unchecked = tk.PhotoImage(data=unchecked_b64)
        self.img_checked = tk.PhotoImage(data=checked_b64)

    def _init_users_tab(self):
        outer = ttk.Frame(self.users_frame)
        outer.pack(fill="both", expand=True, padx=10, pady=10)

        # Toolbar
        bar = ttk.Frame(outer)
        bar.pack(fill="x", pady=(0, 6))
        ttk.Button(bar, text="Import CSV", command=self.import_users_csv).pack(
            side="left", padx=4
        )
        ttk.Button(bar, text="Add User", command=self.add_user_popup).pack(
            side="left", padx=4
        )
        ttk.Button(bar, text="Delete Selected", command=self._bulk_delete_selected).pack(
            side="left", padx=4
        )
        ttk.Button(bar, text="Refresh", command=self.load_users).pack(
            side="left", padx=4
        )
        ttk.Button(bar, text="Clear All Filters", command=self._clear_all_filters).pack(
            side="left", padx=12
        )

        # Tree + scrollbars
        cols = ("ID", "Name", "Email", "Phone", "Company", "Active", "Actions")
        self._user_cols = cols

        tree_wrap = ttk.Frame(outer)
        tree_wrap.pack(fill="both", expand=True)
        self.users_tree = ttk.Treeview(
            tree_wrap, columns=cols, show="tree headings", selectmode="extended"
        )
        ysb = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.users_tree.yview)
        xsb = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self.users_tree.xview)
        self.users_tree.configure(yscroll=ysb.set, xscroll=xsb.set)

        # Master checkbox header (tree column)
        self.users_tree.heading(
            "#0",
            text="",
            image=self.img_unchecked,
            anchor="center",
            command=self._toggle_header_checkbox,
        )
        self.users_tree.column("#0", width=34, anchor="center", stretch=False)

        # Headings with visual dropdown marker; we also catch header clicks via events
        for c in cols:
            label = f"{c} ▾" if c != "Actions" else c
            if c != "Actions":
                self.users_tree.heading(c, text=label, command=(lambda col=c: self._open_filter_menu(col)))
            else:
                self.users_tree.heading(c, text=label)
            width = 120
            if c in ("Email", "Company"):
                width = 200
            if c == "ID":
                width = 70
            if c == "Actions":
                width = 110
            self.users_tree.column(c, width=width, anchor="center")

        self.users_tree.grid(row=0, column=0, sticky="nsew")
        ysb.grid(row=0, column=1, sticky="ns")
        xsb.grid(row=1, column=0, sticky="ew")
        tree_wrap.rowconfigure(0, weight=1)
        tree_wrap.columnconfigure(0, weight=1)

        # Mouse bindings
        self.users_tree.bind("<Button-1>", self._on_users_tree_click)
        self.users_tree.bind("<Double-1>", self._on_users_tree_double_click)
        self.users_tree.bind("<ButtonRelease-3>", self._on_users_tree_right_click)

        # Row context menu
        self._ctx = tk.Menu(self.users_tree, tearoff=0)
        self._ctx.add_command(label="Edit", command=self._ctx_edit_current)
        self._ctx.add_command(label="Delete", command=self._ctx_delete_current)

        self.load_users()

    def _clear_all_filters(self):
        self._filter_state.clear()
        self._refresh_heading_labels()
        self.apply_user_filters()

    # Helpers to compute values by column
    def _value_for_col(self, u, col):
        if col == "ID":
            return str(u["user_id"])
        if col == "Name":
            return f"{u.get('first_name','')} {u.get('last_name','')}".strip()
        if col == "Email":
            return u.get("email", "") or ""
        if col == "Phone":
            return u.get("phone", "") or ""
        if col == "Company":
            return u.get("company_name", "") or ""
        if col == "Active":
            return "Active" if u.get("is_active", 1) else "Inactive"
        return ""

    def _unique_values_for_col(self, col):
        vals = {self._value_for_col(u, col) for u in self.users_data}
        if col == "ID":
            try:
                return [str(x) for x in sorted({int(v) for v in vals})]
            except Exception:
                return sorted(vals)
        return sorted(vals, key=lambda s: (s is None, str(s).lower()))

    def load_users(self):
        try:
            self.users_data = fetch_all_users() or []
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            self.users_data = []
        valid_ids = {u["user_id"] for u in self.users_data}
        self.user_checked = {uid for uid in self.user_checked if uid in valid_ids}
        self.apply_user_filters()

    def apply_user_filters(self):
        self.users_tree.delete(*self.users_tree.get_children())

        def row_matches(u):
            for col, allowed in self._filter_state.items():
                if not allowed:
                    continue
                if self._value_for_col(u, col) not in allowed:
                    return False
            return True

        for u in self.users_data:
            if not row_matches(u):
                continue
            uid = u["user_id"]
            checked = uid in self.user_checked
            img = self.img_checked if checked else self.img_unchecked
            name = self._value_for_col(u, "Name")
            active_label = self._value_for_col(u, "Active")
            self.users_tree.insert(
                "",
                "end",
                iid=str(uid),
                text="",
                image=img,
                values=(
                    uid,
                    name,
                    u.get("email", ""),
                    u.get("phone", ""),
                    u.get("company_name", ""),
                    active_label,
                    "Edit | Delete",
                ),
            )

        # Update header master checkbox state for visible rows
        visible = [int(i) for i in self.users_tree.get_children()]
        if visible and all(v in self.user_checked for v in visible):
            self._header_check_all = True
            self.users_tree.heading("#0", image=self.img_checked)
        else:
            self._header_check_all = False
            self.users_tree.heading("#0", image=self.img_unchecked)

        self._refresh_heading_labels()

    def _refresh_heading_labels(self):
        for c in self._user_cols:
            if c == "Actions":
                self.users_tree.heading(c, text="Actions")
                continue
            mark = "*" if self._filter_state.get(c) else ""
            label = f"{c} ▾{mark}"
            self.users_tree.heading(c, text=label, command=(lambda col=c: self._open_filter_menu(col)))

    # --- New helper: map '#n' to logical column name ---
    def _colid_to_name(self, col_id: str):
        """Map Treeview column id like '#1' to our logical column name.
        Returns '#0' for the tree column, or None if unknown.
        """
        if col_id == "#0":
            return "#0"
        try:
            idx = int(col_id[1:]) - 1
            return self._user_cols[idx]
        except Exception:
            return None

    # ------- header filter menu -------
    def _open_filter_menu(self, col):
        # Popover-like toplevel at mouse position
        win = tk.Toplevel(self)
        win.transient(self)
        win.title(f"Filter: {col}")
        win.resizable(False, False)
        win.overrideredirect(True)
        x, y = self.winfo_pointerx(), self.winfo_pointery()
        win.geometry(f"+{x}+{y}")
        # make sure it appears on top and receives focus, and keep grab so it doesn't auto-close
        try:
            win.lift()
            win.attributes("-topmost", True)
            win.after(150, lambda: win.attributes("-topmost", False))
            win.focus_force()
            win.grab_set()  # keep interactions inside the popover until OK/Cancel
        except Exception:
            pass

        frame = ttk.Frame(win, borderwidth=1, relief="solid")
        frame.pack(fill="both", expand=True)

        # Compute unique values constrained by other active filters (Excel behavior)
        def row_matches_except(u, exclude_col):
            for c_name, allowed in self._filter_state.items():
                if not allowed or c_name == exclude_col:
                    continue
                if self._value_for_col(u, c_name) not in allowed:
                    return False
            return True

        filtered_rows = [u for u in self.users_data if row_matches_except(u, col)]
        if col == "ID":
            try:
                all_values = [
                    str(x)
                    for x in sorted(
                        {int(self._value_for_col(u, col)) for u in filtered_rows}
                    )
                ]
            except Exception:
                all_values = sorted({self._value_for_col(u, col) for u in filtered_rows})
        else:
            all_values = sorted(
                {self._value_for_col(u, col) for u in filtered_rows},
                key=lambda s: (s is None, str(s).lower()),
            )

        current_allowed = self._filter_state.get(col)  # set or None

        # Header bar with search
        bar = ttk.Frame(frame)
        bar.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(bar, text=f"{col}").pack(side="left")
        search_var = tk.StringVar()
        e = ttk.Entry(bar, textvariable=search_var, width=24)
        e.pack(side="right")
        e.focus_set()

        # Select All / Clear buttons
        ctl = ttk.Frame(frame)
        ctl.pack(fill="x", padx=8, pady=(0, 4))
        btn_select_all = ttk.Button(ctl, text="Select All")
        btn_clear = ttk.Button(ctl, text="Clear")
        btn_select_all.pack(side="left")
        btn_clear.pack(side="left", padx=(6, 0))

        # Scrollable checklist
        list_wrap = ttk.Frame(frame)
        list_wrap.pack(padx=8, pady=4)
        canvas = tk.Canvas(list_wrap, width=280, height=220, highlightthickness=0)
        vbar = ttk.Scrollbar(list_wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vbar.set)
        inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.pack(side="left")
        vbar.pack(side="right", fill="y")
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        check_vars = {}  # value -> BooleanVar

        def rebuild():
            for w in inner.winfo_children():
                w.destroy()
            needle = search_var.get().strip().lower()
            for val in all_values:
                text = val if val != "" else "(Blanks)"
                if needle and needle not in str(text).lower():
                    continue
                var = tk.BooleanVar(
                    value=(True if current_allowed is None else (val in current_allowed))
                )
                check_vars[val] = var
                ttk.Checkbutton(inner, text=str(text), variable=var).pack(
                    anchor="w", padx=2
                )

        rebuild()

        def select_all():
            for v in check_vars.values():
                v.set(True)

        def clear_all():
            for v in check_vars.values():
                v.set(False)

        btn_select_all.configure(command=select_all)
        btn_clear.configure(command=clear_all)
        search_var.trace_add("write", lambda *_: rebuild())

        # OK / Cancel
        btns = ttk.Frame(frame)
        btns.pack(fill="x", pady=6, padx=8)

        def do_ok():
            selected = {val for val, var in check_vars.items() if var.get()}
            # If everything is selected (or nothing to filter), clear this column's filter
            if not all_values or len(selected) == len(all_values):
                self._filter_state.pop(col, None)
            else:
                self._filter_state[col] = selected
            win.destroy()
            self.apply_user_filters()

        ttk.Button(btns, text="OK", command=do_ok).pack(side="right")
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="right", padx=(0, 6))

        # Keyboard shortcuts
        win.bind("<Escape>", lambda e: win.destroy())

    # ------- header master checkbox -------
    def _toggle_header_checkbox(self):
        visible_ids = [int(i) for i in self.users_tree.get_children()]
        if not visible_ids:
            return
        if self._header_check_all:
            # Uncheck all visible
            for vid in visible_ids:
                self.user_checked.discard(vid)
                self.users_tree.item(str(vid), image=self.img_unchecked)
            self._header_check_all = False
            self.users_tree.heading("#0", image=self.img_unchecked)
        else:
            # Check all visible
            for vid in visible_ids:
                self.user_checked.add(vid)
                self.users_tree.item(str(vid), image=self.img_checked)
            self._header_check_all = True
            self.users_tree.heading("#0", image=self.img_checked)

    # ------- tree interactions -------
    def _on_users_tree_click(self, event):
        region = self.users_tree.identify("region", event.x, event.y)

        # Handle header left-clicks explicitly (also allow clicks on separator)
        if region in ("heading", "separator"):
            col_id = self.users_tree.identify_column(event.x)  # '#0', '#1', ...
            name = self._colid_to_name(col_id)
            if name == "#0":
                self._toggle_header_checkbox()
            elif name and name != "Actions":
                self._open_filter_menu(name)
            return "break"

        if region not in ("cell", "tree"):
            return

        item = self.users_tree.identify_row(event.y)
        if not item:
            return
        uid = int(item)

        # Checkbox column click
        col = self.users_tree.identify_column(event.x)
        if col == "#0":
            if uid in self.user_checked:
                self.user_checked.remove(uid)
                self.users_tree.item(item, image=self.img_unchecked)
            else:
                self.user_checked.add(uid)
                self.users_tree.item(item, image=self.img_checked)
            return "break"

        # Actions column click
        if col == f"#{len(self._user_cols)+1}":  # Actions
            bbox = self.users_tree.bbox(item, col)
            if not bbox:
                return
            cell_x, cell_w = bbox[0], bbox[2]
            left_half = cell_x + cell_w / 2
            if event.x <= left_half:
                self._edit_user_popup(uid)
            else:
                self._delete_user_confirm(uid)
            return "break"

    def _on_users_tree_double_click(self, event):
        item = self.users_tree.identify_row(event.y)
        if item:
            self._edit_user_popup(int(item))

    def _on_users_tree_right_click(self, event):
        region = self.users_tree.identify("region", event.x, event.y)
        # Right-click on a header OR separator opens the same filter menu (Excel-like)
        if region in ("heading", "separator"):
            col_id = self.users_tree.identify_column(event.x)
            name = self._colid_to_name(col_id)
            if name and name not in ("#0", "Actions"):
                self._open_filter_menu(name)
            return "break"

        item = self.users_tree.identify_row(event.y)
        if not item:
            return
        self.users_tree.selection_set(item)
        self._ctx.tk_popup(event.x_root, event.y_root)

    # Context menu callbacks (for row right-click)
    def _ctx_edit_current(self):
        sel = self.users_tree.selection()
        if sel:
            self._edit_user_popup(int(sel[0]))

    def _ctx_delete_current(self):
        sel = self.users_tree.selection()
        if sel:
            self._delete_user_confirm(int(sel[0]))

    # ------- bulk ops -------
    def _bulk_delete_selected(self):
        if not self.user_checked:
            messagebox.showinfo("Delete Selected", "No users selected.")
            return
        if not messagebox.askyesno(
            "Confirm", f"Delete {len(self.user_checked)} selected users?"
        ):
            return
        ok, fail = 0, 0
        for uid in list(self.user_checked):
            try:
                if delete_user(uid):
                    ok += 1
                else:
                    fail += 1
            except Exception:
                fail += 1
        self.user_checked.clear()
        self.load_users()
        messagebox.showinfo("Delete Selected", f"Deleted: {ok}, Failed: {fail}")

    # ------- CRUD -------
    def _find_user_by_id(self, uid):
        for u in self.users_data:
            if u["user_id"] == uid:
                return u
        return None

    def _edit_user_popup(self, uid):
        u = self._find_user_by_id(uid)
        if not u:
            messagebox.showerror("Edit User", f"User #{uid} not found.")
            return
        popup = tk.Toplevel(self)
        popup.title(f"Edit User #{uid}")
        popup.grab_set()

        labels = [
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "Company",
            "Active (1/0)",
        ]
        values = [
            u.get("first_name", ""),
            u.get("last_name", ""),
            u.get("email", ""),
            u.get("phone", ""),
            u.get("company_name", ""),
            int(u.get("is_active", 1)),
        ]
        entries = []
        for i, (lab, val) in enumerate(zip(labels, values)):
            ttk.Label(popup, text=lab).grid(row=i, column=0, sticky="e", padx=6, pady=5)
            e = ttk.Entry(popup, width=42)
            e.insert(0, str(val))
            e.grid(row=i, column=1, padx=6, pady=5)
            entries.append(e)

        def save():
            try:
                ok = update_user(
                    uid,
                    entries[0].get(),
                    entries[1].get(),
                    entries[2].get(),
                    entries[3].get(),
                    entries[4].get(),
                    int(entries[5].get() or "1"),
                )
                if ok:
                    popup.destroy()
                    self.load_users()
                else:
                    messagebox.showerror("Edit User", "Update failed.")
            except Exception as e:
                messagebox.showerror("Edit User", str(e))

        ttk.Button(popup, text="Save", command=save).grid(
            row=len(labels), column=0, columnspan=2, pady=10
        )

    def _delete_user_confirm(self, uid):
        if not messagebox.askyesno("Confirm", f"Delete user #{uid}?"):
            return
        try:
            if delete_user(uid):
                self.user_checked.discard(uid)
                self.load_users()
            else:
                messagebox.showerror("Delete User", "Delete failed.")
        except Exception as e:
            messagebox.showerror("Delete User", str(e))

    def import_users_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            df = pd.read_csv(path)
            ok = fail = 0
            for _, row in df.iterrows():
                r = add_user(
                    row.get("first_name", ""),
                    row.get("last_name", ""),
                    row.get("email", ""),
                    row.get("phone", ""),
                    row.get("company_name", ""),
                    int(row.get("is_active", 1)),
                )
                ok += 1 if r else 0
                fail += 0 if r else 1
            messagebox.showinfo("Import", f"Success: {ok}, Failed: {fail}")
            self.load_users()
        except Exception as e:
            messagebox.showerror("Import Error", str(e))

    def add_user_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Add User")
        labels = [
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "Company",
            "Active (1/0)",
        ]
        entries = []
        for i, lab in enumerate(labels):
            ttk.Label(popup, text=lab).grid(row=i, column=0, sticky="e", padx=6, pady=5)
            e = ttk.Entry(popup, width=42)
            e.grid(row=i, column=1, padx=6, pady=5)
            entries.append(e)

        def submit():
            try:
                r = add_user(
                    entries[0].get(),
                    entries[1].get(),
                    entries[2].get(),
                    entries[3].get(),
                    entries[4].get(),
                    int(entries[5].get() or "1"),
                )
                if r:
                    popup.destroy()
                    self.load_users()
                else:
                    messagebox.showerror("Add User", "Insert failed.")
            except Exception as e:
                messagebox.showerror("Add User", str(e))

        ttk.Button(popup, text="Add", command=submit).grid(
            row=len(labels), column=0, columnspan=2, pady=10
        )

    # ---------- Campaigns ----------
    def _init_campaigns_tab(self):
        wrapper = ttk.Frame(self.campaigns_frame)
        wrapper.pack(fill="both", expand=True, padx=10, pady=10)
        self.campaigns_tree = ttk.Treeview(
            wrapper, columns=("ID", "Message", "Link"), show="headings"
        )
        for col in ("ID", "Message", "Link"):
            self.campaigns_tree.heading(col, text=col)
            self.campaigns_tree.column(col, width=(80 if col == "ID" else 260), anchor="center")
        self.campaigns_tree.pack(fill="both", expand=True, padx=4, pady=6)

        btns = ttk.Frame(wrapper)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Add Campaign", command=self.add_campaign_popup).pack(
            side="left", padx=4
        )
        ttk.Button(btns, text="Delete Campaign", command=self.delete_selected_campaign).pack(
            side="left", padx=4
        )
        # --- sending respects current Users filters ---
        ttk.Button(btns, text="Send to All", command=self.send_selected_campaign_filtered).pack(
            side="left", padx=4
        )
        ttk.Label(btns, text="(respects current filters)").pack(side="left", padx=(6, 0))
        # Keep WhatsApp open option
        self.keep_open_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            btns,
            text="Keep WhatsApp open after send",
            variable=self.keep_open_var,
        ).pack(side="left", padx=(8, 0))
        # Refresh at the end
        ttk.Button(btns, text="Refresh", command=self.load_campaigns).pack(
            side="left", padx=4
        )
        # Populate table
        self.load_campaigns()

    def load_campaigns(self):
        self.campaigns_tree.delete(*self.campaigns_tree.get_children())
        for c in fetch_all_campaigns() or []:
            self.campaigns_tree.insert(
                "", "end", values=(c["campaign_id"], c["message"], c.get("encrypted_link") or "")
            )

    def add_campaign_popup(self):
        popup = tk.Toplevel(self)
        popup.title("Add Campaign")
        ttk.Label(popup, text="Message").grid(row=0, column=0, sticky="e", padx=6, pady=6)
        e_msg = ttk.Entry(popup, width=80)
        e_msg.grid(row=0, column=1, padx=6, pady=6)
        ttk.Button(
            popup,
            text="Add",
            command=lambda: (
                add_campaign(e_msg.get(), ""),
                popup.destroy(),
                self.load_campaigns(),
            ),
        ).grid(row=1, column=0, columnspan=2, pady=8)

    def delete_selected_campaign(self):
        sel = self.campaigns_tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Please select a campaign.")
            return
        cid = self.campaigns_tree.item(sel[0])["values"][0]
        if messagebox.askyesno("Confirm", f"Delete campaign #{cid}?"):
            delete_campaign(cid)
            self.load_campaigns()

    def _get_visible_user_ids(self):
        return [int(i) for i in self.users_tree.get_children()]

    def send_selected_campaign_filtered(self):
        sel = self.campaigns_tree.selection()
        if not sel:
            messagebox.showinfo("Send", "Please select a campaign to send.")
            return
        cid = self.campaigns_tree.item(sel[0])["values"][0]

        target_ids = self._get_visible_user_ids()
        if not target_ids:
            messagebox.showinfo("Send", "No visible users under current filters.")
            return

        if messagebox.askyesno("Confirm", f"Send campaign #{cid} to all VISIBLE users ({len(target_ids)})?"):
            threading.Thread(
                target=run_whatsapp_campaign,
                kwargs={
                    "campaign_id": cid,
                    "target_user_ids": target_ids,
                    "keep_open": self.keep_open_var.get(),
                },
                daemon=True,
            ).start()
            self.notebook.select(self.run_output_frame)

    # ---------- Dashboard ----------
    def _init_dashboard_tab(self):
        wrapper = ttk.Frame(self.dashboard_frame)
        wrapper.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Label(
            wrapper,
            text="Dashboard: Click 'Refresh' to update statistics.",
            font=("Arial", 14),
        ).pack(pady=10)
        self.dashboard_tree = ttk.Treeview(
            wrapper, columns=("Clicks", "Opens", "Compromises"), show="headings"
        )
        for c in ("Clicks", "Opens", "Compromises"):
            self.dashboard_tree.heading(c, text=c)
            self.dashboard_tree.column(c, width=180, anchor="center")
        self.dashboard_tree.pack(fill="x", padx=10)
        ttk.Button(wrapper, text="Refresh", command=self.refresh_dashboard).pack(pady=12)

    def refresh_dashboard(self):
        self.dashboard_tree.delete(*self.dashboard_tree.get_children())
        tracking = fetch_campaign_status() or []
        clicks = sum(1 for r in tracking if r.get("clicked"))
        opens = sum(1 for r in tracking if r.get("opened"))
        compromises = sum(1 for r in tracking if r.get("compromised"))
        self.dashboard_tree.insert("", "end", values=(clicks, opens, compromises))

    # ---------- Run Output ----------
    def _init_run_output_tab(self):
        wrapper = ttk.Frame(self.run_output_frame)
        wrapper.pack(fill="both", expand=True, padx=8, pady=8)
        ttk.Label(wrapper, text="Live Run Output", font=("Arial", 12, "bold")).pack(
            anchor="w", pady=(0, 6)
        )
        self.run_output_text = ScrolledText(wrapper, height=18, width=120)
        self.run_output_text.pack(fill="both", expand=True)
        ctl = ttk.Frame(wrapper)
        ctl.pack(fill="x", pady=6)
        ttk.Button(
            ctl, text="Clear Output", command=lambda: self.run_output_text.delete("1.0", tk.END)
        ).pack(side="left")

    # ---------- Admin ----------
    def unlock_admin_tab(self):
        pw_popup = tk.Toplevel(self)
        pw_popup.title("Admin Login")
        pw_popup.geometry("320x120")
        tk.Label(pw_popup, text="Admin Password:").pack(pady=10)
        pw_entry = tk.Entry(pw_popup, show="*", width=25)
        pw_entry.pack()
        info = tk.Label(pw_popup, text="", fg="red")
        info.pack()

        def check_pw():
            admin_pass = os.getenv("ADMIN_PASS", "wps123")
            if pw_entry.get() == admin_pass:
                pw_popup.destroy()
                if not self.admin_tab_added:
                    self._init_admin_tools_tab()
                self.notebook.select(self.admin_tab_index)
            else:
                info.config(text="Wrong password. Try again.")

        tk.Button(pw_popup, text="Login", command=check_pw).pack(pady=8)
        pw_entry.focus_set()

    def _init_admin_tools_tab(self):
        self.admin_frame = ttk.Frame(self.notebook)
        self.admin_tab_index = self.notebook.index("end")
        self.notebook.add(self.admin_frame, text="Admin Tools")
        self.admin_tab_added = True

        row = 0
        ttk.Label(self.admin_frame, text="Fernet Key Management", font=("Arial", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=8
        )
        row += 1
        ttk.Button(
            self.admin_frame, text="Generate Fernet Key", command=self.generate_key_from_gui
        ).grid(row=row, column=0, sticky="w", padx=4)
        self.key_display = tk.Text(self.admin_frame, height=1, width=60)
        self.key_display.grid(row=row, column=1, padx=4)
        row += 1

        ttk.Label(self.admin_frame, text="Encrypt/Decrypt Token", font=("Arial", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=8
        )
        row += 1
        ttk.Label(self.admin_frame, text="User ID:").grid(row=row, column=0, sticky="e")
        self.encrypt_user_id = tk.Entry(self.admin_frame, width=8)
        self.encrypt_user_id.grid(row=row, column=1, sticky="w")
        ttk.Label(self.admin_frame, text="Campaign ID:").grid(row=row, column=2, sticky="e")
        self.encrypt_campaign_id = tk.Entry(self.admin_frame, width=8)
        self.encrypt_campaign_id.grid(row=row, column=3, sticky="w")
        ttk.Button(self.admin_frame, text="Encrypt", command=self.encrypt_from_gui).grid(
            row=row, column=4, sticky="w"
        )
        self.encrypted_token_display = tk.Text(self.admin_frame, height=1, width=60)
        self.encrypted_token_display.grid(row=row + 1, column=0, columnspan=5)
        row += 2

        ttk.Label(self.admin_frame, text="Token:").grid(row=row, column=0, sticky="e")
        self.decrypt_token_entry = tk.Entry(self.admin_frame, width=40)
        self.decrypt_token_entry.grid(row=row, column=1, sticky="w")
        ttk.Button(self.admin_frame, text="Decrypt", command=self.decrypt_from_gui).grid(
            row=row, column=2, sticky="w"
        )
        self.decrypted_token_display = tk.Text(self.admin_frame, height=1, width=40)
        self.decrypted_token_display.grid(row=row + 1, column=0, columnspan=3)
        row += 2

        ttk.Label(self.admin_frame, text="View Error Logs", font=("Arial", 12, "bold")).grid(
            row=row, column=0, sticky="w", pady=8
        )
        row += 1
        ttk.Button(
            self.admin_frame, text="Show Error Logs", command=self.show_error_logs_from_gui
        ).grid(row=row, column=0, sticky="w")
        self.error_logs_box = tk.Text(self.admin_frame, height=8, width=80)
        self.error_logs_box.grid(row=row + 1, column=0, columnspan=5)

    # admin helpers
    def generate_key_from_gui(self):
        try:
            from generate_key import ensure_secret_key_in_env

            key = ensure_secret_key_in_env()
            self.key_display.delete("1.0", tk.END)
            self.key_display.insert(tk.END, key)
            messagebox.showinfo("Fernet Key", ".env updated with a new key.")
        except Exception as e:
            self.key_display.delete("1.0", tk.END)
            self.key_display.insert(tk.END, f"Error: {e}")

    def encrypt_from_gui(self):
        try:
            from encrypt_utils import generate_encrypted_token

            uid = int(self.encrypt_user_id.get())
            cid = int(self.encrypt_campaign_id.get())
            token = generate_encrypted_token(uid, cid)
            self.encrypted_token_display.delete("1.0", tk.END)
            self.encrypted_token_display.insert(tk.END, token)
        except Exception as e:
            self.encrypted_token_display.delete("1.0", tk.END)
            self.encrypted_token_display.insert(tk.END, f"Error: {e}")

    def decrypt_from_gui(self):
        try:
            from encrypt_utils import decrypt_token

            token = self.decrypt_token_entry.get()
            uid, cid = decrypt_token(token)
            self.decrypted_token_display.delete("1.0", tk.END)
            if uid is not None:
                self.decrypted_token_display.insert(
                    tk.END, f"User ID: {uid}, Campaign ID: {cid}"
                )
            else:
                self.decrypted_token_display.insert(tk.END, "Invalid token")
        except Exception as e:
            self.decrypted_token_display.delete("1.0", tk.END)
            self.decrypted_token_display.insert(tk.END, f"Error: {e}")

    def show_error_logs_from_gui(self):
        try:
            logs = fetch_error_logs() or []
            self.error_logs_box.delete("1.0", tk.END)
            for log in logs:
                self.error_logs_box.insert(
                    tk.END,
                    f"[{log['occurred_at']}] {log['component']} – {log['error_message']}\n",
                )
        except Exception as e:
            self.error_logs_box.delete("1.0", tk.END)
            self.error_logs_box.insert(tk.END, f"Error: {e}")


if __name__ == "__main__":
    app = WPSGUI()
    app.mainloop()
