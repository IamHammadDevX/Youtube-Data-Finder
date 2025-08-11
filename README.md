# 📺 YouTube Finder  
**A powerful, open-source desktop tool for bulk YouTube discovery and analysis.**

---

## 📑 Table of Contents
- [Overview](#overview)  
- [Features](#features)  
- [Quick Start](#quick-start)  
- [Installation](#installation)  
- [Usage](#usage)  
  - [GUI Mode](#gui-mode)  
  - [Headless Mode](#headless-mode)  
  - [Scheduling](#scheduling)  
- [Settings File](#settings-file)  
- [CSV Output](#csv-output)  
- [Troubleshooting](#troubleshooting)  
- [Contributing](#contributing)  
- [License](#license)

---

## 📌 Overview
YouTube Finder lets you **search thousands of videos** in one click, **filter by every metric** (views, age, subscribers, duration, region, etc.) and **export clean CSVs** ready for Excel or BI tools.

- **100 % local** – no cloud, no telemetry.
- **Windows / macOS / Linux** – pure Python.
- **API-quota-smart** – stops before you burn credits.

---

## ✨ Features

| Feature | Status |
|---------|--------|
| Bulk keyword search | ✅ |
| Duration, views, subscriber filters | ✅ |
| **Upload-date range** (min / max) | ✅ |
| **Time-frame views** (e.g., 1 M in 30 days) | ✅ |
| Region & language targeting | ✅ |
| **Auto-clear history** after X days | ✅ |
| **Daily scheduler** (GUI picker + Task Scheduler) | ✅ |
| **Scrollable GUI** (fits small screens) | ✅ |
| **UTF-8-BOM CSV** (Excel-ready) | ✅ |
| Sortable / filterable results table | ✅ |
| 90 % quota warning + auto-stop | ✅ |
| Headless CLI for scripts | ✅ |

---

## 🚀 Quick Start (30 s)

1. **Clone or download** this repo.
2. **Install Python 3.10+**.
3. **Install deps**:

```bash
pip install -r requirements.txt
```

4. **Set API key** (once):

- Windows  
  ```cmd
  set YOUTUBE_API_KEY=YOUR_KEY_HERE
  ```

- macOS / Linux  
  ```bash
  export YOUTUBE_API_KEY=YOUR_KEY_HERE
  ```

5. **Run GUI**:

```bash
python app_tkinter.py
```

6. **Enter keywords**, set filters, click **Start Now**.

---

## 🛠 Installation

### 1. Requirements

```text
pandas>=2.0
requests>=2.31
tkcalendar>=1.6   # for date pickers
isodate>=0.6      # parse ISO8601 durations
```

Install with:

```bash
pip install -r requirements.txt
```

### 2. Obtain YouTube API Key

- Go to [Google Cloud Console](https://console.cloud.google.com/).
- Create project → Enable **YouTube Data API v3**.
- Create **API key** (no OAuth needed).
- Copy key into environment variable as shown above.

---

## 🎯 Usage

### GUI Mode

![Screenshot](docs/screenshot.png)

| Control | Purpose |
|---------|---------|
| Keywords | One per line |
| Duration | Any / Short / Medium / Long / Custom |
| Views / Subscribers | Min / Max numeric |
| Time-frame views | ≥ daily views within N days |
| Region / Language | ISO codes |
| Date Filters | Min / Max upload date |
| History retention | Auto-clear after X days |
| Daily Schedule | Pick time, enable checkbox, click “Save Schedule” |
| Start Now | Manual run |
| Export | Save results to CSV |

### Headless Mode

```bash
python app_headless.py --settings settings.json
```

### Scheduling (Windows)

1. GUI → set schedule time → click **Save Schedule**.
2. Run `schedule_helper.bat` **as Administrator** (creates Task Scheduler job).
3. Or manually create a task that runs:
   ```cmd
   python app_headless.py --settings settings.json
   ```

---

## ⚙️ Settings File (`settings.json`)

```json
{
  "keywords": "python tutorial\nproduct review",
  "duration": "Medium (4-20 min)",
  "duration_min": "",
  "duration_max": "",
  "views_min": "1000",
  "views_max": "1000000",
  "subs_min": "",
  "subs_max": "",
  "region": "US",
  "language": "en",
  "pages": "2",
  "api_cap": "9500",
  "skip_hidden": true,
  "fresh_search": false,
  "days_back": "30",
  "min_daily_views": "50000",
  "history_keep_days": "30",
  "min_date": "2023-01-01",
  "max_date": "2024-12-31",
  "schedule_time": "09:00",
  "schedule_enabled": false
}
```

---

## 📊 CSV Output

Columns (UTF-8-BOM):

```
title,description,tags,video_url,video_id,channel_title,channel_id,subscriber_count,view_count,duration_minutes,published_at,keyword
```

Each row = one video, ready for Excel / Power BI / Python.

---

## 🛠 Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ModuleNotFoundError` | `pip install -r requirements.txt` |
| `quota_exceeded` | Lower `api_cap` or wait 24 h |
| GUI tiny | Use the **scrollbar** on the left panel |
| CSV shows ??? | Ensure Excel opens as UTF-8-BOM |

---

## 🤝 Contributing

Pull requests welcome!  
Guidelines:

- Follow PEP 8.
- Add tests for new filters.
- Update README / changelog.

---

## 📜 License

MIT License — see [LICENSE](LICENSE).

---

## 📞 Support

Open an [issue](https://github.com/your-org/youtube-finder/issues) or reach out on Discord.