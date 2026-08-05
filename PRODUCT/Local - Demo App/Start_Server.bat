@echo off
title QA Confirm Gate - Local Demo App
cd /d "%~dp0source"

echo ==================================================
echo STARTING QA CONFIRM GATE LOCAL DEMO APP...
echo Open your browser and navigate to: http://localhost:8000
echo ==================================================
echo.

if exist "%~dp0python_env\python.exe" (
    "%~dp0python_env\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
) else if exist "%~dp0python_env\Scripts\python.exe" (
    "%~dp0python_env\Scripts\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
) else (
    python -m uvicorn main:app --host 127.0.0.1 --port 8000
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ==================================================
    echo Error starting QA Confirm Gate Server!
    echo ==================================================
    pause
)
