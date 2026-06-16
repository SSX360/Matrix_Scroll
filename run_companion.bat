@echo off
title Cursor Co-pilot Desktop Companion
cd /d "%~dp0"
echo Starting Cursor Co-pilot desktop companion...
call run_desktop_companion.bat
if errorlevel 1 (
    echo.
    echo Error: Failed to start. Make sure the virtual environment and python are set up.
    pause
)
