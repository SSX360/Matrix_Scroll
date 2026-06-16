@echo off
title Cursor Co-pilot Desktop Companion Launcher
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo Starting Cursor Co-pilot backend and floating companion...
%PYTHON% desktop_launcher.py

if errorlevel 1 (
  echo.
  echo Failed to launch Cursor Co-pilot desktop companion.
  pause
)
