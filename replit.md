# YouTube Finder

## Overview

YouTube Finder is a desktop application for searching and filtering YouTube videos with comprehensive API quota management. It provides both GUI and headless operation modes for searching YouTube content based on multiple criteria, with intelligent duplicate prevention and CSV-based data storage. The application is designed to respect YouTube API quota limits while providing comprehensive video metadata for analysis and export.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

**2025-08-11**: 
- Switched from PySimpleGUI to Tkinter due to compatibility issues
- Created new Tkinter-based GUI (`app_tkinter.py`) with improved layout
- Cleaned up project by removing irrelevant files
- Application now runs successfully with desktop GUI interface

## System Architecture

### Application Structure
The system follows a modular architecture with clear separation of concerns:

- **Main GUI Application** (`app_tkinter.py`) - Tkinter-based desktop interface
- **Headless Application** (`app_headless.py`) - Command-line version for scheduled operations  
- **YouTube API Integration** (`youtube_api.py`) - Handles all YouTube Data API v3 interactions
- **CSV Data Management** (`csv_handler.py`) - Manages all file-based data operations
- **Configuration Management** (`config_manager.py`) - Handles settings persistence in JSON format
- **Utility Functions** (`utils.py`) - Common helper functions for data processing

### Data Storage Strategy
The application uses a file-based approach without databases:

- **Results Storage**: Daily CSV files in `export/results_YYYY-MM-DD.csv` format
- **Duplicate Prevention**: History tracking via `data/seen_history.csv`
- **Configuration**: JSON-based settings storage in `settings.json`
- **Logging**: Optional run logs in `logs/runs.csv`

This approach provides simplicity, portability, and easy data inspection without database dependencies.

### Search and Filtering Architecture
The search system implements multi-stage filtering:

1. **Keyword Processing**: Multi-line keyword input with individual search execution
2. **API-Level Filtering**: Duration, region, and language filters applied at API level
3. **Post-Processing Filters**: View count, subscriber count, and duplicate filtering
4. **Quota Management**: Real-time quota tracking with configurable limits

### Threading and Concurrency
The GUI application uses threading to prevent UI blocking:

- **Search Operations**: Executed in separate threads
- **Progress Updates**: Real-time UI updates during search operations
- **Cancellation Support**: User can stop searches mid-operation

### Error Handling and Validation
Comprehensive error handling includes:

- **API Key Validation**: Format and environment variable checks
- **Rate Limiting**: Built-in delays between API requests
- **Quota Protection**: Pre-request quota validation
- **Data Validation**: CSV structure validation and missing column handling

## External Dependencies

### Required APIs
- **YouTube Data API v3**: Primary service for video search and metadata retrieval
  - Requires API key via `YOUTUBE_API_KEY` environment variable
  - Implements quota tracking with 10,000 daily unit limit
  - Uses search, videos, and channels endpoints

### Python Dependencies
- **tkinter**: Desktop GUI framework for the main application interface (built-in with Python)
- **requests**: HTTP client for YouTube API communication
- **pandas**: Data manipulation and CSV handling
- **isodate**: ISO 8601 duration parsing for video length processing
- **pyyaml**: YAML configuration support (optional)

### System Dependencies
- **Python 3.10+**: Runtime requirement with tkinter support
- **Windows Task Scheduler**: Optional integration for automated searches (Windows)
- **Cross-platform**: Application works on Windows, macOS, and Linux

### File System Structure
The application creates and manages several directories:
- `data/`: Internal data storage (history files)
- `export/`: Search results output location
- `logs/`: Application logging (optional)