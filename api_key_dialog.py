import tkinter as tk
from tkinter import ttk

class ApiKeyDialog(tk.Toplevel):
    def __init__(self, parent, current_key="", *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.title("Enter YouTube API Key")
        self.resizable(False, False)
        self.grab_set()  # Modal
        self.result = None

        # Style (do NOT set any global background or font for ttk widgets)
        self.configure(bg="#f4f6fb")
        self.columnconfigure(0, weight=1)

        # Use default system font for ttk widgets
        style = ttk.Style(self)
        style.configure('TButton', font=('Segoe UI', 10, 'bold'))

        # Heading (local bg for label using tk.Label)
        heading = tk.Label(
            self,
            text="YouTube API Key",
            font=('Segoe UI', 13, 'bold'),
            bg='#f4f6fb'
        )
        heading.grid(row=0, column=0, pady=(16, 6), padx=24, sticky="w")

        # Description (local bg for label using tk.Label)
        desc = tk.Label(
            self,
            text="Paste your YouTube Data API key below.\nYou can get one from Google Cloud Console.",
            font=('Segoe UI', 10),
            bg='#f4f6fb'
        )
        desc.grid(row=1, column=0, padx=24, sticky="w")

        # Entry field (use default font for ttk.Entry)
        self.api_key_var = tk.StringVar(value=current_key)
        entry = ttk.Entry(self, textvariable=self.api_key_var, show="*", width=38)
        entry.grid(row=2, column=0, padx=24, pady=(10, 8), sticky="we")
        entry.focus()

        # Show/hide checkbox
        self.show_var = tk.BooleanVar(value=False)
        show_btn = ttk.Checkbutton(
            self,
            text="Show API key",
            variable=self.show_var,
            command=lambda: self.toggle_show(entry)
        )
        show_btn.grid(row=3, column=0, padx=24, sticky="w")

        # Button frame
        button_frame = ttk.Frame(self)
        button_frame.grid(row=4, column=0, pady=18, padx=24, sticky="e")

        save_btn = ttk.Button(button_frame, text="Save", width=10, command=self.on_save)
        save_btn.pack(side="left", padx=(0, 10))
        cancel_btn = ttk.Button(button_frame, text="Cancel", width=10, command=self.on_cancel)
        cancel_btn.pack(side="left")

        # Keyboard shortcuts
        self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.on_cancel())

        # Increase dialog height to fit all widgets
        self.geometry("430x240")

    def toggle_show(self, entry):
        entry.config(show='' if self.show_var.get() else '*')

    def on_save(self):
        key = self.api_key_var.get().strip()
        if key:
            self.result = key
            self.destroy()
        else:
            self.bell()

    def on_cancel(self):
        self.result = None
        self.destroy()

def get_api_key_dialog(parent, current_key=""):
    dialog = ApiKeyDialog(parent, current_key)
    parent.wait_window(dialog)
    return dialog.result