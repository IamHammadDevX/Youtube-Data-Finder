import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import pandas as pd
import os
import json
import threading
import time
import webbrowser
from datetime import datetime
from youtube_api import YouTubeSearcher
from csv_handler import CSVHandler
from config_manager import ConfigManager
from utils import format_duration, parse_duration_minutes, validate_api_key, passes_timeframe_view_filter, quota_warning_threshold, passes_upload_date_filter
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

class YouTubeFinderTkinter:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Finder")
        self.root.geometry("1400x800")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize components
        self.config_manager = ConfigManager()
        self.csv_handler = CSVHandler()
        self.youtube_searcher = None
        self.search_thread = None
        self.stop_search = False
        
        # Initialize API key
        api_key = os.getenv('YOUTUBE_API_KEY', '')
        if not api_key:
            messagebox.showerror('API Key Error', 
                               'YouTube API Key not found!\nPlease set YOUTUBE_API_KEY environment variable.')
            self.root.quit()
            return
        
        if not validate_api_key(api_key):
            messagebox.showerror('API Key Error', 
                               'Invalid YouTube API Key format!\nPlease check your YOUTUBE_API_KEY environment variable.')
            self.root.quit()
            return
            
        self.youtube_searcher = YouTubeSearcher(api_key)
        self.history_keep_days_var = tk.StringVar()
        self.history_keep_days_var.set(str(self.config_manager.load_settings().get('history_keep_days', '')))
        self.schedule_time_var = tk.StringVar()
        self.schedule_enabled_var = tk.BooleanVar()
        
        # UI State
        self.results_df = pd.DataFrame()
        self.quota_used = 0
        self.search_stats = {'scanned': 0, 'kept': 0, 'skipped': 0}
        
        # Create directories
        os.makedirs('data', exist_ok=True)
        os.makedirs('export', exist_ok=True)
        os.makedirs('logs', exist_ok=True)
        
        # Create UI
        self.create_widgets()
        self.load_settings()
        
    def create_widgets(self):
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Left panel - Controls
        left_frame = ttk.LabelFrame(main_frame, text="Search Controls", padding="10")
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Right panel - Status and Results
        right_frame = ttk.LabelFrame(main_frame, text="Results", padding="10")
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        self.create_left_panel(left_frame)
        self.create_right_panel(right_frame)
        
    def create_left_panel(self, parent):
        # --- 1) scrollable container ---------------------------------------
        canvas = tk.Canvas(parent, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # --- 2) all widgets go into scrollable_frame -----------------------
        parent = scrollable_frame   # so the rest of the code stays identical
        row = 0

        # Keywords
        ttk.Label(parent, text="Keywords/Phrases (one per line):", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        row += 1
        self.keywords_text = scrolledtext.ScrolledText(parent, width=40, height=6)
        self.keywords_text.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        row += 1

        # Duration
        ttk.Label(parent, text="Duration:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        row += 1
        self.duration_var = tk.StringVar(value="Any")
        duration_combo = ttk.Combobox(parent, textvariable=self.duration_var,
                                    values=['Any', 'Short (<4 min)', 'Medium (4-20 min)', 'Long (>20 min)', 'Custom'],
                                    state='readonly')
        duration_combo.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 4))
        duration_combo.bind('<<ComboboxSelected>>', self.on_duration_change)
        row += 1

        # Custom duration controls
        duration_frame = ttk.Frame(parent)
        duration_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        ttk.Label(duration_frame, text="Min (min):").grid(row=0, column=0, sticky=tk.W)
        self.duration_min_var = tk.StringVar()
        self.duration_min_entry = ttk.Entry(duration_frame, textvariable=self.duration_min_var, width=10, state='disabled')
        self.duration_min_entry.grid(row=0, column=1, padx=(3, 6))
        ttk.Label(duration_frame, text="Max:").grid(row=0, column=2, sticky=tk.W)
        self.duration_max_var = tk.StringVar()
        self.duration_max_entry = ttk.Entry(duration_frame, textvariable=self.duration_max_var, width=10, state='disabled')
        self.duration_max_entry.grid(row=0, column=3, padx=(3, 0))
        row += 1

        # Views
        ttk.Label(parent, text="Views:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        row += 1
        views_frame = ttk.Frame(parent)
        views_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        ttk.Label(views_frame, text="Min:").grid(row=0, column=0, sticky=tk.W)
        self.views_min_var = tk.StringVar()
        ttk.Entry(views_frame, textvariable=self.views_min_var, width=15).grid(row=0, column=1, padx=(3, 6))
        ttk.Label(views_frame, text="Max:").grid(row=0, column=2, sticky=tk.W)
        self.views_max_var = tk.StringVar()
        ttk.Entry(views_frame, textvariable=self.views_max_var, width=15).grid(row=0, column=3, padx=(3, 0))
        row += 1

        # Subscribers
        ttk.Label(parent, text="Subscribers:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        row += 1
        subs_frame = ttk.Frame(parent)
        subs_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        ttk.Label(subs_frame, text="Min:").grid(row=0, column=0, sticky=tk.W)
        self.subs_min_var = tk.StringVar()
        ttk.Entry(subs_frame, textvariable=self.subs_min_var, width=15).grid(row=0, column=1, padx=(3, 6))
        ttk.Label(subs_frame, text="Max:").grid(row=0, column=2, sticky=tk.W)
        self.subs_max_var = tk.StringVar()
        ttk.Entry(subs_frame, textvariable=self.subs_max_var, width=15).grid(row=0, column=3, padx=(3, 0))
        row += 1

        # Timeframe views
        ttk.Label(parent, text="Time-frame Views:", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        row += 1
        tf_frame = ttk.Frame(parent)
        tf_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        ttk.Label(tf_frame, text="≥").grid(row=0, column=0, sticky=tk.W)
        self.min_daily_views_var = tk.StringVar()
        ttk.Entry(tf_frame, textvariable=self.min_daily_views_var, width=12).grid(row=0, column=1, padx=(2, 3))
        ttk.Label(tf_frame, text="daily views within").grid(row=0, column=2, padx=(3, 2))
        self.days_back_var = tk.StringVar()
        ttk.Entry(tf_frame, textvariable=self.days_back_var, width=5).grid(row=0, column=3, padx=(2, 3))
        ttk.Label(tf_frame, text="days").grid(row=0, column=4)
        row += 1

        # Upload-date range (NEW)
                # Upload-date range (NEW)
        date_frame = ttk.LabelFrame(parent, text="Upload Date Range", padding="5")
        date_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        row += 1

        ttk.Label(date_frame, text="From:").grid(row=0, column=0, sticky=tk.W)
        self.upload_min_var = tk.StringVar()
        min_entry = DateEntry(date_frame, textvariable=self.upload_min_var,
                              date_pattern='yyyy-mm-dd', width=12)
        min_entry.grid(row=0, column=1, padx=(3, 6))

        ttk.Label(date_frame, text="To:").grid(row=0, column=2, sticky=tk.W)
        self.upload_max_var = tk.StringVar()
        max_entry = DateEntry(date_frame, textvariable=self.upload_max_var,
                              date_pattern='yyyy-mm-dd', width=12)
        max_entry.grid(row=0, column=3, padx=(3, 0))

        # Allow clearing with backspace / delete
        for entry, var in ((min_entry, self.upload_min_var),
                           (max_entry, self.upload_max_var)):
            entry.bind('<KeyRelease>', lambda e, v=var: v.set('') if e.widget.get().strip() == '' else None)

        row += 1

        # Region / Language
        region_lang_frame = ttk.Frame(parent)
        region_lang_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        ttk.Label(region_lang_frame, text="Region:").grid(row=0, column=0, sticky=tk.W)
        self.region_var = tk.StringVar()
        ttk.Combobox(region_lang_frame, textvariable=self.region_var,
                    values=['', 'US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP', 'IN', 'BR'], width=8).grid(
            row=0, column=1, padx=(3, 6))
        ttk.Label(region_lang_frame, text="Language:").grid(row=0, column=2, sticky=tk.W)
        self.language_var = tk.StringVar()
        ttk.Combobox(region_lang_frame, textvariable=self.language_var,
                    values=['', 'en', 'es', 'fr', 'de', 'ja', 'pt', 'hi', 'ru', 'ko'], width=8).grid(
            row=0, column=3, padx=(3, 0))
        row += 1

        # Pages / API cap
        pages_api_frame = ttk.Frame(parent)
        pages_api_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        ttk.Label(pages_api_frame, text="Pages/keyword:").grid(row=0, column=0, sticky=tk.W)
        self.pages_var = tk.StringVar(value="2")
        ttk.Entry(pages_api_frame, textvariable=self.pages_var, width=8).grid(row=0, column=1, padx=(3, 6))
        ttk.Label(pages_api_frame, text="Daily API cap:").grid(row=0, column=2, sticky=tk.W)
        self.api_cap_var = tk.StringVar(value="9500")
        ttk.Entry(pages_api_frame, textvariable=self.api_cap_var, width=8).grid(row=0, column=3, padx=(3, 0))
        row += 1

        # Checkboxes
        self.skip_hidden_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(parent, text="Skip hidden subscriber counts", variable=self.skip_hidden_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))
        row += 1

        self.fresh_search_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="Fresh search (clear history)", variable=self.fresh_search_var).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))
        row += 1

        # History retention
        ttk.Label(parent, text="History retention (days, 0 = keep):", font=('Arial', 10, 'bold')).grid(
            row=row, column=0, columnspan=2, sticky=tk.W, pady=(0, 2))
        row += 1
        hist_frame = ttk.Frame(parent)
        hist_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        self.history_keep_days_entry = ttk.Entry(hist_frame, textvariable=self.history_keep_days_var, width=5)
        self.history_keep_days_entry.grid(row=0, column=0, padx=(0, 3))
        ttk.Button(hist_frame, text="Clear now", command=self.clear_history_now).grid(row=0, column=1, padx=(6, 0))
        row += 1

        # Daily schedule
        sched_frame = ttk.LabelFrame(parent, text="Daily Schedule", padding="5")
        sched_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        row += 1
        ttk.Checkbutton(sched_frame, text="Enable daily run at", variable=self.schedule_enabled_var).grid(
            row=0, column=0, sticky=tk.W)
        self.time_entry = ttk.Entry(sched_frame, textvariable=self.schedule_time_var, width=5)
        self.time_entry.grid(row=0, column=1, padx=(3, 0))
        ttk.Label(sched_frame, text="(HH:MM 24h)").grid(row=0, column=2, padx=(3, 0))
        row += 1

        # Buttons
        button_frame = ttk.Frame(parent)
        button_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 6))
        self.start_button = ttk.Button(button_frame, text="Start Now", command=self.start_search)
        self.start_button.grid(row=0, column=0, padx=(0, 3))
        ttk.Button(button_frame, text="Save Schedule...", command=self.save_schedule).grid(row=0, column=1, padx=3)
        self.stop_button = ttk.Button(button_frame, text="Stop Search", command=self.stop_search_func, state='disabled')
        self.stop_button.grid(row=0, column=2, padx=(3, 0))
        
    def create_right_panel(self, parent):
        # Status section
        status_frame = ttk.LabelFrame(parent, text="Status", padding="5")
        status_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        parent.columnconfigure(0, weight=1)
        
        self.quota_est_label = ttk.Label(status_frame, text="Estimated quota for this run: 0")
        self.quota_est_label.grid(row=0, column=0, sticky=tk.W)
        
        self.quota_used_label = ttk.Label(status_frame, text="Current quota used: 0")
        self.quota_used_label.grid(row=1, column=0, sticky=tk.W)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=5)
        status_frame.columnconfigure(0, weight=1)
        
        # Stats
        stats_frame = ttk.Frame(status_frame)
        stats_frame.grid(row=3, column=0, sticky=(tk.W, tk.E))
        self.scanned_label = ttk.Label(stats_frame, text="Scanned: 0")
        self.scanned_label.grid(row=0, column=0, padx=(0, 10))
        self.kept_label = ttk.Label(stats_frame, text="Kept: 0")
        self.kept_label.grid(row=0, column=1, padx=(0, 10))
        self.skipped_label = ttk.Label(stats_frame, text="Skipped: 0")
        self.skipped_label.grid(row=0, column=2)
        
                        # FILTER BAR (above the table)
        filter_frame = ttk.LabelFrame(parent, text="Filters", padding="5")
        filter_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        col = 0
        ttk.Label(filter_frame, text="Title:").grid(row=0, column=col); col += 1
        self.filter_title_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_title_var, width=20) \
            .grid(row=0, column=col, padx=(0, 8)); col += 1

        ttk.Label(filter_frame, text="Min Views:").grid(row=0, column=col); col += 1
        self.filter_views_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_views_var, width=8) \
            .grid(row=0, column=col, padx=(0, 8)); col += 1

        ttk.Label(filter_frame, text="Min Daily:").grid(row=0, column=col); col += 1
        self.filter_daily_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_daily_var, width=8) \
            .grid(row=0, column=col, padx=(0, 8)); col += 1

        # ---- NEW: upload-date pickers ----
        ttk.Label(filter_frame, text="From:").grid(row=0, column=col); col += 1
        self.filter_min_date_var = tk.StringVar()
        DateEntry(filter_frame, textvariable=self.filter_min_date_var,
                  date_pattern='yyyy-mm-dd', width=10) \
            .grid(row=0, column=col, padx=(0, 8)); col += 1

        ttk.Label(filter_frame, text="To:").grid(row=0, column=col); col += 1
        self.filter_max_date_var = tk.StringVar()
        DateEntry(filter_frame, textvariable=self.filter_max_date_var,
                  date_pattern='yyyy-mm-dd', width=10) \
            .grid(row=0, column=col); col += 1

        # trace all for live filtering
        for v in (self.filter_title_var, self.filter_views_var,
                  self.filter_daily_var, self.filter_min_date_var,
                  self.filter_max_date_var):
            v.trace_add('write', self.on_filter_change)
        
        # Results table
        table_frame = ttk.Frame(parent)
        table_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent.rowconfigure(2, weight=1)
        
        # Treeview with scrollbars
        self.tree = ttk.Treeview(table_frame, columns=('Title', 'Channel', 'Views', 'Duration', 'Published', 'Keyword','Description', 'Tags'), show='headings', height=15)
        
                # Tree-view with full columns
        self.tree = ttk.Treeview(
            table_frame,
            columns=('Title', 'Channel', 'Views', 'Duration', 'Published', 'Keyword',
                     'Description', 'Tags'),
            show='headings',
            height=15)

        # Column specs
        cols = [
            ('Title', 300), ('Channel', 150), ('Views', 100, int),
            ('Duration', 80), ('Published', 100, 'date'),
            ('Keyword', 120), ('Description', 250), ('Tags', 200)
        ]
        for col, w, *typ in cols:
            self.tree.heading(
                col,
                text=col,
                command=lambda c=col, t=typ[0] if typ else 'str': self.sort_column(c, t))
            self.tree.column(col, width=w)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Action buttons
        action_frame = ttk.Frame(parent)
        action_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.open_video_button = ttk.Button(action_frame, text="Open Video", command=self.open_video, state='disabled')
        self.open_video_button.grid(row=0, column=0, padx=(0, 5))
        
        self.open_channel_button = ttk.Button(action_frame, text="Open Channel", command=self.open_channel, state='disabled')
        self.open_channel_button.grid(row=0, column=1, padx=(0, 5))
        
        self.export_button = ttk.Button(action_frame, text="Export Results", command=self.export_results, state='disabled')
        self.export_button.grid(row=0, column=2)
        
        # Bind tree selection
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
    
    def sort_column(self, col, dtype):
        """Cycle asc -> desc -> no-sort for the clicked column."""
        data = [(self.tree.set(k, col), k) for k in self.tree.get_children('')]

        # Determine next state
        if not data:
            return
        current = self.tree.heading(col, 'text').split()
        if current[-1:] == ['▲']:
            reverse, arrow = True, '▼'
        elif current[-1:] == ['▼']:
            reverse, arrow = False, ''
        else:
            reverse, arrow = False, '▲'

        # Type-cast for correct order
        def cast(val):
            if dtype == int:
                try:
                    return int(val.replace(',', ''))
                except ValueError:
                    return 0
            elif dtype == 'date':
                try:
                    return pd.to_datetime(val)
                except Exception:
                    return pd.NaT
            else:
                return val.lower()

        data.sort(key=lambda t: cast(t[0]), reverse=reverse)

        # Re-insert in new order
        for index, (_, k) in enumerate(data):
            self.tree.move(k, '', index)

        # Update header arrow
        self.tree.heading(col, text=f"{col.split()[0]} {arrow}".strip())
    
    def clear_history_now(self):
        """Immediately wipe the history file and refresh UI."""
        self.csv_handler.clear_history_now()
        messagebox.showinfo("History", "View history has been cleared.")
        
    def on_duration_change(self, event=None):
        if self.duration_var.get() == 'Custom':
            self.duration_min_entry.config(state='normal')
            self.duration_max_entry.config(state='normal')
        else:
            self.duration_min_entry.config(state='disabled')
            self.duration_max_entry.config(state='disabled')
        self.update_quota_estimate()
    
    def on_filter_change(self, *args):
        """Refresh the table whenever any filter field changes."""
        if self.results_df.empty:
            return

        df = self.results_df.copy()

        # ---------------- Title keyword (case-insensitive) ----------------
        title_kw = self.filter_title_var.get().strip().lower()
        if title_kw:
            df = df[df['title'].str.contains(title_kw, na=False, case=False)]

        # ---------------- Min total views --------------------------------
        try:
            min_v = int(self.filter_views_var.get().strip())
            df = df[df['view_count'] >= min_v]
        except ValueError:
            pass

        # ---------------- Min daily views --------------------------------
        try:
            min_daily = float(self.filter_daily_var.get().strip())
            # Convert to naive UTC once
            df['published_at'] = pd.to_datetime(
                df['published_at'], errors='coerce', utc=True).dt.tz_localize(None)
            now = pd.Timestamp.utcnow().tz_localize(None)
            df['age_days'] = (now - df['published_at']).dt.days.clip(lower=1)
            df = df[df['view_count'] / df['age_days'] >= min_daily]
        except ValueError:
            pass

        # ---------------- Upload-date range filters (NEW) ----------------
        min_date_str = self.filter_min_date_var.get().strip()
        max_date_str = self.filter_max_date_var.get().strip()

        if min_date_str or max_date_str:
            # Ensure datetime column exists
            df['published_at'] = pd.to_datetime(
                df['published_at'], errors='coerce', utc=True).dt.tz_localize(None)

            if min_date_str:
                min_dt = pd.to_datetime(min_date_str)
                df = df[df['published_at'] >= min_dt]

            if max_date_str:
                max_dt = pd.to_datetime(max_date_str) + pd.Timedelta(days=1)  # inclusive
                df = df[df['published_at'] < max_dt]

        # ---------------- Re-populate Tree-view --------------------------
        self.tree.delete(*self.tree.get_children())
        for _, row in df.iterrows():
            title = row['title'][:50] + '...' if len(row['title']) > 50 else row['title']
            desc  = row['description'][:60] + '...' if len(row['description']) > 60 else row['description']
            tags  = row['tags'][:40] + '...' if len(row['tags']) > 40 else row['tags']
            self.tree.insert('', tk.END, values=(
                title,
                row['channel_title'],
                f"{int(row['view_count']):,}",
                format_duration(row['duration_minutes']),
                str(row['published_at'])[:10],
                row['keyword'],
                desc,
                tags
            ))
    
    def on_tree_select(self, event=None):
        selection = self.tree.selection()
        if selection:
            self.open_video_button.config(state='normal')
            self.open_channel_button.config(state='normal')
        else:
            self.open_video_button.config(state='disabled')
            self.open_channel_button.config(state='disabled')
    
    def update_quota_estimate(self):
        keywords_text = self.keywords_text.get("1.0", tk.END).strip()
        try:
            pages_per_keyword = int(self.pages_var.get() or '2')
        except ValueError:
            pages_per_keyword = 2
        
        estimated_quota = self.estimate_quota(keywords_text, pages_per_keyword)
        self.quota_est_label.config(text=f"Estimated quota for this run: {estimated_quota}")
    
    def estimate_quota(self, keywords, pages_per_keyword):
        try:
            keyword_count = len([k.strip() for k in keywords.split('\n') if k.strip()])
            if keyword_count == 0:
                return 0
            
            # search.list: 100 units per call
            search_calls = keyword_count * int(pages_per_keyword)
            search_quota = search_calls * 100
            
            # Estimate results (conservative: 30 results per page)
            estimated_results = search_calls * 30
            
            # videos.list: 1 unit per call (batches of 50)
            video_calls = (estimated_results + 49) // 50
            video_quota = video_calls * 1
            
            # channels.list: 1 unit per call (batches of 50)  
            channel_calls = video_calls
            channel_quota = channel_calls * 1
            
            total_quota = search_quota + video_quota + channel_quota
            return total_quota
            
        except Exception:
            return 0
    
    def start_search(self):
        # Validate inputs
        keywords_text = self.keywords_text.get("1.0", tk.END).strip()
        if not keywords_text:
            messagebox.showerror('Input Error', 'Please enter at least one keyword!')
            return
        
        keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
        
        try:
            pages_per_keyword = int(self.pages_var.get() or '2')
            api_cap = int(self.api_cap_var.get() or '9500')
        except ValueError:
            messagebox.showerror('Input Error', 'Pages per keyword and API cap must be valid numbers!')
            return
        
        # Validate quota
        estimated_quota = self.estimate_quota(keywords_text, pages_per_keyword)
        if estimated_quota > api_cap:
            messagebox.showerror('Quota Error', 
                               f'Estimated quota ({estimated_quota}) exceeds your daily cap ({api_cap})!\n'
                               'Reduce keywords or pages per keyword.')
            return
        
        # Prepare search config
        search_config = {
            'keywords': keywords,
            'pages_per_keyword': pages_per_keyword,
            'api_cap': api_cap,
            'duration_filter': self.duration_var.get(),
            'duration_min': self.duration_min_var.get(),
            'duration_max': self.duration_max_var.get(),
            'views_min': self.views_min_var.get(),
            'views_max': self.views_max_var.get(),
            'subs_min': self.subs_min_var.get(),
            'subs_max': self.subs_max_var.get(),
            'region': self.region_var.get(),
            'language': self.language_var.get(),
            'skip_hidden': self.skip_hidden_var.get(),
            'fresh_search': self.fresh_search_var.get()
        }
        
        # Update UI state
        self.start_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.stop_search = False
        self.search_stats = {'scanned': 0, 'kept': 0, 'skipped': 0}
        self.progress_var.set(0)
        
        # Start search thread
        self.search_thread = threading.Thread(target=self.search_worker, args=(search_config,))
        self.search_thread.daemon = True
        self.search_thread.start()
    
    def search_worker(self, config):
        try:
            # Clear history if fresh search
            if config['fresh_search']:
                self.csv_handler.clear_history()

            # Auto-clear old history before the main loop
            keep_days_str = config.get('history_keep_days', '').strip()
            if keep_days_str.isdigit():
                keep_days = int(keep_days_str)
                self.csv_handler.clear_history_older_than(keep_days)

            # Initialize results
            all_results = []
            self.quota_used = 0
            total_keywords = len(config['keywords'])

            # timeframe-view parameters
            days_back = config.get('days_back', '').strip()
            min_daily_views = config.get('min_daily_views', '').strip()

            # upload-date range parameters (NEW)
            upload_date_min = config.get('upload_date_min', '').strip()
            upload_date_max = config.get('upload_date_max', '').strip()

            # Build RFC-3339 timestamps for YouTube API
            def _to_rfc(dt_str):
                return f"{dt_str}T00:00:00Z" if dt_str else ''
            published_after  = _to_rfc(upload_date_min)
            published_before = _to_rfc(upload_date_max)

            # 90 % warning threshold
            warning_limit = quota_warning_threshold(config['api_cap'])

            for i, keyword in enumerate(config['keywords']):
                if self.stop_search:
                    break

                # Update progress
                progress = int((i / total_keywords) * 100)
                self.root.after(0, lambda p=progress: self.progress_var.set(p))

                try:
                    # Search videos for this keyword WITH date bounds
                    videos = self.youtube_searcher.search_videos(
                        query=keyword,
                        max_pages=config['pages_per_keyword'],
                        region=config['region'],
                        language=config['language'],
                        duration_filter=config['duration_filter'],
                        quota_limit=config['api_cap'] - self.quota_used,
                        published_after=published_after,
                        published_before=published_before
                    )

                    self.quota_used += self.youtube_searcher.quota_used

                    # update quota label with color change
                    def _update_quota_label():
                        self.quota_used_label.config(text=f"Current quota used: {self.quota_used}")
                        if warning_limit and self.quota_used >= warning_limit:
                            self.quota_used_label.config(foreground='red')
                        else:
                            self.quota_used_label.config(foreground='black')
                    self.root.after(0, _update_quota_label)

                    # 90 % warning pop-up & auto-stop
                    if warning_limit and self.quota_used >= warning_limit:
                        self.root.after(
                            0,
                            lambda: messagebox.showwarning(
                                'Quota Warning',
                                f'You have reached 90 % of your daily quota ({self.quota_used}/{config["api_cap"]}).\n'
                                'Search will stop to avoid over-use.'))
                        break

                    # Apply filters and deduplication
                    for video in videos:
                        if self.stop_search:
                            break

                        self.search_stats['scanned'] += 1

                        # Check if already seen
                        if self.csv_handler.is_video_seen(video['video_id']):
                            self.search_stats['skipped'] += 1
                            continue

                        # Apply duration filter
                        duration_minutes = parse_duration_minutes(video.get('duration', ''))
                        if not self.passes_duration_filter(duration_minutes, config):
                            self.search_stats['skipped'] += 1
                            continue

                        # Apply view filter
                        view_count = int(video.get('view_count', 0))
                        if not self.passes_view_filter(view_count, config):
                            self.search_stats['skipped'] += 1
                            continue

                        # timeframe view filter
                        if not passes_timeframe_view_filter(
                                view_count,
                                video.get('published_at', ''),
                                days_back,
                                min_daily_views):
                            self.search_stats['skipped'] += 1
                            continue

                        # upload-date range filter (post-fetch sanity check)
                        if not passes_upload_date_filter(
                                video.get('published_at', ''),
                                upload_date_min,
                                upload_date_max):
                            self.search_stats['skipped'] += 1
                            continue

                        # Apply subscriber filter
                        subscriber_count = int(video.get('subscriber_count', 0))
                        if config['skip_hidden'] and video.get('hidden_subscriber_count', False):
                            self.search_stats['skipped'] += 1
                            continue

                        if not self.passes_subscriber_filter(subscriber_count, config):
                            self.search_stats['skipped'] += 1
                            continue

                        # Add keyword to video data
                        video['keyword'] = keyword
                        video['duration_minutes'] = duration_minutes
                        all_results.append(video)
                        self.search_stats['kept'] += 1

                        # Update stats display
                        self.root.after(0, self.update_stats_display)

                    # Check hard quota limit (absolute stop)
                    if self.quota_used >= config['api_cap']:
                        self.root.after(0, lambda: messagebox.showinfo('Quota Limit',
                                                                    'Daily quota limit reached!'))
                        break

                except Exception as e:
                    print(f'Error searching {keyword}: {str(e)}')
                    continue

            # Save results
            if all_results and not self.stop_search:
                results_df = pd.DataFrame(all_results)
                today = datetime.now().strftime('%Y-%m-%d')
                results_file = f'export/results_{today}.csv'

                self.csv_handler.save_results(results_df, results_file)
                self.csv_handler.update_history([r['video_id'] for r in all_results])

                # Update UI with results
                self.results_df = results_df
                self.root.after(0, self.update_results_table)
                self.root.after(0, lambda: self.export_button.config(state='normal'))
                self.root.after(
                    0,
                    lambda: messagebox.showinfo(
                        'Search Complete',
                        f'Found {len(all_results)} videos!\nResults saved to: {results_file}'))
            else:
                self.root.after(
                    0,
                    lambda: messagebox.showinfo('Search Complete',
                                                'No results found matching criteria'))

        except Exception as e:
            self.root.after(
                0,
                lambda: messagebox.showerror('Search Error',
                                            f'An error occurred during search: {str(e)}'))

        finally:
            # Re-enable start button
            self.root.after(0, lambda: self.start_button.config(state='normal'))
            self.root.after(0, lambda: self.stop_button.config(state='disabled'))
            self.root.after(0, lambda: self.progress_var.set(100))

            # ---- RESET date filters ----
            self.root.after(0, lambda: self.filter_min_date_var.set(''))
            self.root.after(0, lambda: self.filter_max_date_var.set(''))
            
    
    def passes_duration_filter(self, duration_minutes, config):
        duration_filter = config['duration_filter']
        
        if duration_filter == 'Any':
            return True
        elif duration_filter == 'Short (<4 min)':
            return duration_minutes < 4
        elif duration_filter == 'Medium (4-20 min)':
            return 4 <= duration_minutes <= 20
        elif duration_filter == 'Long (>20 min)':
            return duration_minutes > 20
        elif duration_filter == 'Custom':
            duration_min = config['duration_min']
            duration_max = config['duration_max']
            min_dur = float(duration_min) if duration_min else 0
            max_dur = float(duration_max) if duration_max else float('inf')
            return min_dur <= duration_minutes <= max_dur
        return True
    
    def passes_view_filter(self, view_count, config):
        views_min = config['views_min']
        views_max = config['views_max']
        
        if views_min and view_count < int(views_min):
            return False
        if views_max and view_count > int(views_max):
            return False
        return True
    
    def passes_subscriber_filter(self, subscriber_count, config):
        subs_min = config['subs_min']
        subs_max = config['subs_max']
        
        if subs_min and subscriber_count < int(subs_min):
            return False
        if subs_max and subscriber_count > int(subs_max):
            return False
        return True
    
    def update_stats_display(self):
        self.scanned_label.config(text=f"Scanned: {self.search_stats['scanned']}")
        self.kept_label.config(text=f"Kept: {self.search_stats['kept']}")
        self.skipped_label.config(text=f"Skipped: {self.search_stats['skipped']}")
    
    def update_results_table(self):
        """Populate (or re-populate) the Tree-view from self.results_df."""
        # 1. Clear existing rows
        for item in self.tree.get_children():
            self.tree.delete(item)

        if self.results_df.empty:
            return

        # 2. Apply live filters (if any)
        df = self.results_df.copy()

        # Title keyword
        title_kw = self.filter_title_var.get().strip().lower()
        if title_kw:
            df = df[df['title'].str.contains(title_kw, na=False, case=False)]

        # Min total views
        try:
            min_v = int(self.filter_views_var.get().strip())
            df = df[df['view_count'] >= min_v]
        except ValueError:
            pass

        # Min daily views (UTC-safe)
                # Min and max date filters
                # Min daily views (no apply, no tz headaches)
        try:
            min_daily = float(self.filter_daily_var.get().strip())
            # Convert to naive UTC once
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce', utc=True).dt.tz_localize(None)
            now = pd.Timestamp.utcnow().tz_localize(None)
            df['age_days'] = (now - df['published_at']).dt.days.clip(lower=1)
            df = df[df['view_count'] / df['age_days'] >= min_daily]
        except ValueError:
            pass

        # 3. Insert rows into Tree-view
        for _, row in df.iterrows():
            title = row['title'][:50] + '...' if len(row['title']) > 50 else row['title']
            desc  = row['description'][:60] + '...' if len(row['description']) > 60 else row['description']
            tags  = row['tags'][:40] + '...' if len(row['tags']) > 40 else row['tags']
            self.tree.insert('', tk.END, values=(
                title,
                row['channel_title'],
                f"{int(row['view_count']):,}",
                format_duration(row['duration_minutes']),
                str(row['published_at'])[:10],
                row['keyword'],
                desc,
                tags
            ))
    
    def stop_search_func(self):
        self.stop_search = True
        self.start_button.config(state='normal')
        self.stop_button.config(state='disabled')
    
    def open_video(self):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            # Get the original row index
            for idx, row in self.results_df.iterrows():
                title = row['title'][:50] + '...' if len(row['title']) > 50 else row['title']
                if self.tree.item(item, 'values')[0] == title:
                    webbrowser.open(row['video_url'])
                    break
    
    def open_channel(self):
        selection = self.tree.selection()
        if selection:
            item = selection[0]
            # Get the original row index
            for idx, row in self.results_df.iterrows():
                title = row['title'][:50] + '...' if len(row['title']) > 50 else row['title']
                if self.tree.item(item, 'values')[0] == title:
                    channel_url = f"https://www.youtube.com/channel/{row['channel_id']}"
                    webbrowser.open(channel_url)
                    break
    
    def export_results(self):
        if self.results_df.empty:
            messagebox.showwarning('No Data', 'No results to export!')
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Results"
        )
        
        if filename:
            try:
                self.csv_handler.save_results(self.results_df, filename)
                messagebox.showinfo('Export Complete', f'Results exported to: {filename}')
            except Exception as e:
                messagebox.showerror('Export Error', f'Failed to export results: {str(e)}')
    
    def save_schedule(self):
        """Save GUI settings AND create a schedule file / command."""
        settings = self.get_current_settings()

        # Validate schedule
        if settings.get('schedule_enabled'):
            try:
                datetime.strptime(settings['schedule_time'], '%H:%M')
            except ValueError:
                messagebox.showerror('Schedule Error', 'Enter a valid HH:MM time!')
                return

        # Save JSON
        if self.config_manager.save_settings(settings):
            cmd = self.config_manager.create_task_scheduler_command()
            if settings.get('schedule_enabled'):
                # Create scheduler file
                sched_file = 'daily_schedule.bat'
                with open(sched_file, 'w', encoding='utf-8') as f:
                    f.write(f'@echo off\n"{cmd["python_exe"]}" "{cmd["script_path"]}" --settings "{cmd["settings_path"]}"\n')
                messagebox.showinfo(
                    'Schedule Saved',
                    f'Settings saved.\n'
                    f'Batch file created: {sched_file}\n\n'
                    f'Use Windows Task Scheduler to run daily at {settings["schedule_time"]}')
            else:
                messagebox.showinfo('Schedule Saved', 'Settings saved (no daily schedule).')
        else:
            messagebox.showerror('Save Error', 'Could not save settings!')
    
    def get_current_settings(self):
        return {
            'keywords': self.keywords_text.get("1.0", tk.END).strip(),
            'duration': self.duration_var.get(),
            'duration_min': self.duration_min_var.get(),
            'duration_max': self.duration_max_var.get(),
            'views_min': self.views_min_var.get(),
            'views_max': self.views_max_var.get(),
            'subs_min': self.subs_min_var.get(),
            'subs_max': self.subs_max_var.get(),
            'days_back': self.days_back_var.get().strip(),
            'min_daily_views': self.min_daily_views_var.get().strip(),
            'history_keep_days': self.history_keep_days_var.get().strip(),
            'schedule_time': self.schedule_time_var.get().strip(),
            'schedule_enabled': self.schedule_enabled_var.get(),
            'upload_date_min': self.upload_min_var.get().strip(),
            'upload_date_max': self.upload_max_var.get().strip(),
            'region': self.region_var.get(),
            'language': self.language_var.get(),
            'pages': self.pages_var.get(),
            'api_cap': self.api_cap_var.get(),
            'skip_hidden': self.skip_hidden_var.get(),
            'fresh_search': self.fresh_search_var.get()
        }
    
    def load_settings(self):
        settings = self.config_manager.load_settings()
        
        self.keywords_text.delete("1.0", tk.END)
        self.keywords_text.insert("1.0", settings.get('keywords', ''))
        self.duration_var.set(settings.get('duration', 'Any'))
        self.duration_min_var.set(settings.get('duration_min', ''))
        self.duration_max_var.set(settings.get('duration_max', ''))
        self.views_min_var.set(settings.get('views_min', ''))
        self.views_max_var.set(settings.get('views_max', ''))
        self.subs_min_var.set(settings.get('subs_min', ''))
        self.subs_max_var.set(settings.get('subs_max', ''))
        self.days_back_var.set(settings.get('days_back', ''))
        self.min_daily_views_var.set(settings.get('min_daily_views', ''))
        self.history_keep_days_var.set(settings.get('history_keep_days', ''))
        self.upload_min_var.set(settings.get('upload_date_min', ''))
        self.upload_max_var.set(settings.get('upload_date_max', ''))
        self.schedule_time_var.set(settings.get('schedule_time', ''))
        self.schedule_enabled_var.set(settings.get('schedule_enabled', False))
        self.region_var.set(settings.get('region', ''))
        self.language_var.set(settings.get('language', ''))
        self.pages_var.set(settings.get('pages', '2'))
        self.api_cap_var.set(settings.get('api_cap', '9500'))
        self.skip_hidden_var.set(settings.get('skip_hidden', True))
        self.fresh_search_var.set(settings.get('fresh_search', False))
        
        # Trigger duration change to enable/disable custom fields
        self.on_duration_change()
        self.update_quota_estimate()
    
    def run(self):
        self.root.mainloop()

def main():
    try:
        app = YouTubeFinderTkinter()
        app.run()
    except Exception as e:
        print(f"Error starting application: {str(e)}")

if __name__ == '__main__':
    main()