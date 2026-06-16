@echo off
REM Cursor Docs Assistant - Windows launcher
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on your PATH. Install Python 3.9+ from python.org and retry.
  pause
  exit /b 1
)

if not exist ".venv" (
  echo Creating virtual environment...
  python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo Starting Cursor Docs Assistant...
python app.py
pause
