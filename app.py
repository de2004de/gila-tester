"""Desktop interface for running local checks and reviewing their results."""

import csv
import os
import runpy
import tkinter as tk
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import filedialog, messagebox, ttk


COLUMNS = ("Check", "Result", "Status")


def load_checks():
    location = os.environ.get("GILA_CHECKS_FILE")
    if not location:
        return {}
    path = Path(location).expanduser().resolve(strict=True)
    checks = runpy.run_path(str(path)).get("checks")
    if not isinstance(checks, dict) or not all(
        isinstance(name, str) and name.strip() and callable(check)
        for name, check in checks.items()
    ):
        raise ValueError("The local file must define a checks dictionary.")
    return checks


def run_checks(checks, events):
    try:
        for name, check in checks:
            try:
                value, passed = check()
                if not isinstance(passed, bool):
                    raise ValueError("A check must return a result and a boolean.")
                row = (name, str(value), "Passed" if passed else "Failed")
            except Exception as error:
                row = (name, str(error), "Error")
            events.put(row)
    finally:
        events.put(None)


def read_report(stream):
    reader = csv.reader(stream, strict=True)
    if next(reader, None) != list(COLUMNS):
        raise ValueError("Choose a report saved by this application.")
    rows = list(reader)
    if any(len(row) != len(COLUMNS) for row in rows):
        raise ValueError("The report contains an incomplete row.")
    return rows


class MainWindow:
    def __init__(self, window, checks):
        self.window = window
        self.checks = checks
        self.events = Queue()
        self.busy = False
        window.title("Gila Test Console")
        panel = ttk.Frame(window, padding=12)
        panel.pack(fill="both", expand=True)

        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=6)
        self.selection = ttk.Combobox(actions, values=list(checks), state="readonly")
        self.selection.pack(side="left", fill="x", expand=True)
        if checks:
            self.selection.current(0)
        self.selected = ttk.Button(actions, text="Run selected", command=self.run_selected)
        self.all_checks = ttk.Button(actions, text="Run all", command=lambda: self.start(checks.items()))
        self.selected.pack(side="left", padx=4)
        self.all_checks.pack(side="left")

        self.tree = ttk.Treeview(panel, columns=COLUMNS, show="headings")
        for column in COLUMNS:
            self.tree.heading(column, text=column)
            self.tree.column(column, anchor="center")
        self.tree.pack(fill="both", expand=True, pady=6)

        footer = ttk.Frame(panel)
        footer.pack(fill="x")
        self.status = ttk.Label(footer, text="Ready" if checks else "No local checks configured")
        self.status.pack(side="left")
        self.save = ttk.Button(footer, text="Save report", command=self.save_report)
        self.open = ttk.Button(footer, text="Open report", command=self.open_report)
        self.save.pack(side="right")
        self.open.pack(side="right", padx=4)
        self.refresh()
        self.window.protocol("WM_DELETE_WINDOW", self.close)

    def refresh(self):
        enabled = self.checks and not self.busy
        for button in (self.selected, self.all_checks):
            button.configure(state="normal" if enabled else "disabled")
        self.open.configure(state="disabled" if self.busy else "normal")
        self.save.configure(state="normal" if self.tree.get_children() and not self.busy else "disabled")

    def run_selected(self):
        name = self.selection.get()
        if name in self.checks:
            self.start([(name, self.checks[name])])

    def start(self, checks):
        if self.busy:
            return
        self.tree.delete(*self.tree.get_children())
        self.busy = True
        self.status.configure(text="Running checks…")
        self.refresh()
        Thread(target=run_checks, args=(list(checks), self.events)).start()
        self.poll()

    def poll(self):
        while True:
            try:
                row = self.events.get_nowait()
            except Empty:
                self.window.after(50, self.poll)
                return
            if row is None:
                self.busy = False
                self.status.configure(text="Run complete")
                self.refresh()
                return
            self.tree.insert("", "end", values=row)

    def close(self):
        if self.busy:
            messagebox.showinfo("Run in progress", "Wait for the current run to finish.", parent=self.window)
        else:
            self.window.destroy()

    def save_report(self):
        path = filedialog.asksaveasfilename(parent=self.window, defaultextension=".csv", filetypes=[("CSV report", "*.csv")])
        if path:
            try:
                with open(path, "w", encoding="utf-8", newline="") as stream:
                    writer = csv.writer(stream)
                    writer.writerow(COLUMNS)
                    writer.writerows(self.tree.item(item, "values") for item in self.tree.get_children())
            except OSError as error:
                messagebox.showerror("Save report", str(error), parent=self.window)

    def open_report(self):
        path = filedialog.askopenfilename(parent=self.window, filetypes=[("CSV report", "*.csv")])
        if path:
            try:
                with open(path, encoding="utf-8-sig", newline="") as stream:
                    rows = read_report(stream)
            except (OSError, ValueError, csv.Error) as error:
                messagebox.showerror("Open report", str(error), parent=self.window)
                return
            self.tree.delete(*self.tree.get_children())
            for row in rows:
                self.tree.insert("", "end", values=row)
            self.status.configure(text=Path(path).name)
            self.refresh()


if __name__ == "__main__":
    root = tk.Tk()
    try:
        local_checks = load_checks()
    except Exception as error:
        messagebox.showerror("Local checks", str(error), parent=root)
        local_checks = {}
    MainWindow(root, local_checks)
    root.mainloop()
