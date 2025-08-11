@echo off
echo YouTube Finder - Schedule Setup Helper
echo =====================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo Running as Administrator - OK
    echo.
) else (
    echo ERROR: This script must be run as Administrator
    echo Right-click on schedule_helper.bat and select "Run as administrator"
    pause
    exit /b 1
)

REM Check if settings.json exists
if not exist "settings.json" (
    echo ERROR: settings.json not found!
    echo Please run the main application first and use "Save Schedule..."
    pause
    exit /b 1
)

REM Get current directory
set CURRENT_DIR=%CD%

REM Check if Python is available
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Python not found in PATH
    echo Please ensure Python is installed and added to PATH
    pause
    exit /b 1
)

REM Check if app_headless.py exists
if not exist "app_headless.py" (
    echo ERROR: app_headless.py not found in current directory
    echo Please ensure all application files are present
    pause
    exit /b 1
)

echo Current directory: %CURRENT_DIR%
echo Found settings.json: OK
echo Python available: OK
echo app_headless.py found: OK
echo.

echo Setting up Windows Task Scheduler job...
echo.

REM Create the scheduled task
schtasks /create ^
  /tn "YouTube Finder Daily Search" ^
  /tr "python \"%CURRENT_DIR%\app_headless.py\" --settings \"%CURRENT_DIR%\settings.json\"" ^
  /sc daily ^
  /st 09:00 ^
  /sd %date% ^
  /f

if %errorLevel% == 0 (
    echo.
    echo SUCCESS: Scheduled task created successfully!
    echo.
    echo Task Name: YouTube Finder Daily Search
    echo Schedule: Daily at 9:00 AM
    echo Command: python app_headless.py --settings settings.json
    echo Working Directory: %CURRENT_DIR%
    echo.
    echo You can modify the schedule using Windows Task Scheduler:
    echo 1. Press Win+R, type "taskschd.msc", press Enter
    echo 2. Find "YouTube Finder Daily Search" in the task list
    echo 3. Right-click and select "Properties" to modify settings
    echo.
    echo To test the task immediately:
    echo schtasks /run /tn "YouTube Finder Daily Search"
) else (
    echo.
    echo ERROR: Failed to create scheduled task
    echo Please check the error messages above
    echo.
    echo You can create the task manually:
    echo 1. Open Task Scheduler (taskschd.msc)
    echo 2. Create Basic Task
    echo 3. Set trigger (daily, time, etc.)
    echo 4. Action: Start a program
    echo 5. Program: python
    echo 6. Arguments: "%CURRENT_DIR%\app_headless.py" --settings "%CURRENT_DIR%\settings.json"
    echo 7. Start in: %CURRENT_DIR%
)

echo.
echo Additional Notes:
echo - Ensure YOUTUBE_API_KEY environment variable is set system-wide
echo - The task will run with your user account permissions
echo - Check Task Scheduler History tab for execution results
echo - Logs will be saved in the logs/ directory

echo.
pause
