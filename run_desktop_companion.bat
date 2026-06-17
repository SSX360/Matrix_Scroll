@echo off
title Digital Rain Desktop Companion Launcher
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
  set "PYTHON=.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo Starting Digital Rain backend and floating companion...
%PYTHON% desktop_launcher.py

if errorlevel 1 (
  echo.
  echo Failed to launch Digital Rain desktop companion.
  pause
)
