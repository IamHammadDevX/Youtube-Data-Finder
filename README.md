# YouTube Finder

A Windows desktop application for searching and filtering YouTube videos with comprehensive API quota management and CSV-based data storage.

## Features

- **Advanced Search**: Search YouTube with multiple keywords/phrases
- **Smart Filtering**: Filter by views, subscriber count, video duration, region, and language
- **Quota Management**: Never exceed your daily YouTube API quota (respects 10,000 free-unit limit)
- **Duplicate Prevention**: Tracks seen videos across days to avoid duplicates
- **Complete Metadata**: Saves title, description, tags, URLs, and channel information
- **CSV Export**: All data stored in CSV files (no database required)
- **Scheduling Support**: Run searches automatically with Windows Task Scheduler

## Requirements

- Windows 10/11
- Python 3.10 or higher
- YouTube Data API v3 key

## Installation

### 1. Install Python
1. Download Python 3.10+ from [python.org](https://python.org)
2. **Important**: Check "Add to PATH" during installation

### 2. Install Required Packages
Open Command Prompt and run:
```bash
pip install requests isodate pandas PySimpleGUI pyyaml
